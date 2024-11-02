import asyncio
import json
import uuid
from typing import Union

import aiofiles
import aiohttp
import humanfriendly
from interactions import *
from interactions.api.events import MessageCreate, Component
import config_loader
from utilities.profile.badge_manager import increment_value
from utilities.message_decorations import *

from database import UserData, ServerData

from utilities.transmission_connection_manager import *


class TransmissionModule(Extension):

    @slash_command(description='Transmit to over servers!')
    async def transmit(self, ctx: SlashContext):
        pass

    @transmit.subcommand(sub_cmd_description='Connect to a server you already know.')
    async def call(self, ctx: SlashContext):

        server_data: ServerData = await ServerData(ctx.guild_id).fetch()
        
        can_transmit = server_data.transmit_channel
        server_ids = server_data.transmittable_servers
        
        if attempting_to_connect(ctx.guild.id):

            return await fancy_message(ctx, '[ This server is already transmitting! ]', ephemeral=True)

        if not can_transmit:

            return await fancy_message(ctx,
                                       '[ This server has opted to disable call transmissions or has simply not set a channel. ]',
                                       ephemeral=True)

        if not server_ids:

            return await fancy_message(ctx,
                                       '[ This server doesn\'t know any other servers! Connect using ``/transmit connect``! ]',
                                       ephemeral=True)

        options = []

        server_name = ''

        for server_id, name in server_ids.items():
            options.append(
                StringSelectOption(
                    label=name,
                    value=server_id
                )
            )

        server_list = StringSelectMenu(
            options,
            custom_id=str(ctx.guild.id),
            placeholder='Connect to...',
        )

        await ctx.send(components=server_list, ephemeral=True)

        select_results = await self.bot.wait_for_component(components=server_list)

        other_server = int(select_results.ctx.values[0])
        other_server_data: ServerData = await ServerData(other_server).fetch()
        
        if other_server in server_data.blocked_servers:
            return await fancy_message(select_results.ctx, '[ Sorry, but this server is blocked. ]', color=0xfa272d, ephemeral=True)
        
        if ctx.guild_id in other_server_data.blocked_servers:
            return await fancy_message(select_results.ctx, '[ Sorry, but this server has blocked you. ]', color=0xfa272d, ephemeral=True)

        get_channel: ServerData = await ServerData(other_server).fetch()
        get_channel = get_channel.transmit_channel

        if not get_channel:

            return await fancy_message(select_results.ctx,
                                       '[ Sorry, but the server you selected has opted to disable call transmissions, or simply has not set a channel. ]',
                                       color=0xfa272d, ephemeral=True)

        other_server_channel: GuildText = await self.bot.fetch_channel(get_channel, force=True)

        server_name = other_server_channel.guild.name

        connect_button = Button(
            style=ButtonStyle.PRIMARY,
            label='Answer',
            custom_id='answer_phone'
        )

        disconnect_button = Button(
            style=ButtonStyle.DANGER,
            label='Decline',
            custom_id='decline_phone'
        )

        embed_one = fancy_embed(f'[ Calling **{server_name}**... <a:loading:1026539890382483576> ]')

        embed_timeout_one = fancy_embed('``[ Sorry! You took too long to respond! ]``', color=0xfa272d)
        embed_timeout_two = fancy_embed('``[ Sorry! The other server took too long to respond! ]``', color=0xfa272d)

        embed_cancel_one = fancy_embed('``[ Successfully Declined. ]``', color=0xfa272d)
        embed_cancel_two = fancy_embed('``[ Sorry! The other server declined the call! ]``', color=0xfa272d)

        message = await select_results.ctx.send(embed=embed_one)

        other_server_message = await fancy_message(other_server_channel, f'[ **{ctx.guild.name}** is calling you! ]', components=[connect_button, disconnect_button])

        try:
            other_server_component: Component = await self.bot.wait_for_component(components=[connect_button, disconnect_button], timeout=60)
        except:

            await other_server_message.edit(embed=embed_timeout_one, components=[])
            await message.edit(embed=embed_timeout_two)
            return
        
        other_server_ctx = other_server_component.ctx

        await other_server_ctx.defer(edit_origin=True)

        button_id = other_server_ctx.custom_id

        if button_id == 'decline_phone':

            await other_server_message.edit(embed=embed_cancel_one, components=[])
            await message.edit(embed=embed_cancel_two)
        else:

            create_connection(ctx.guild_id, ctx.channel_id)
            connect_to_transmission(other_server, other_server_channel.id)

            await asyncio.gather(
                self.on_transmission(ctx.user, message, ctx.guild_id),
                self.on_transmission(other_server_ctx.user, other_server_message, other_server)
            ) # type: ignore

    @transmit.subcommand(sub_cmd_description='Transmit to another server.')
    async def connect(self, ctx: SlashContext):
        
        await ctx.defer()
        server_data: ServerData = await ServerData(ctx.guild_id).fetch()

        if available_initial_connections(server_data.blocked_servers):
            
            if attempting_to_connect(ctx.guild_id):

                return await fancy_message(ctx, '[ This server is already transmitting! ]', ephemeral=True)
            
            create_connection(ctx.guild_id, ctx.channel_id)

            embed = await self.embed_manager('initial_connection')

            cancel = Button(
                style=ButtonStyle.DANGER,
                label='Cancel',
                custom_id='haha cancel go brrr'
            )

            msg = await ctx.send(embeds=embed, components=cancel)

            async def check_(component: Component):
                if ctx.user.id == component.ctx.user.id:
                    return True
                else:
                    await component.ctx.send(
                        f'[ Only the initiator of this transmission ({ctx.user.mention}) can cancel it! ]',
                        ephemeral=True)
                    return False

            task = asyncio.create_task(self.bot.wait_for_component(components=cancel, check=check_))

            while not connection_alive(ctx.guild_id):
                done, _ = await asyncio.wait({task}, timeout=1)

                if not done:
                    continue

                remove_connection(ctx.guild_id)

                button_ctx: Component = task.result()
                
                await button_ctx.ctx.defer(edit_origin=True)

                embed = await self.on_cancel('manual', ctx.guild_id, button_ctx.ctx)

                await msg.edit(embeds=embed, components=[])
                return

            await increment_value(ctx, 'times_transmitted', 1, ctx.user)

            await self.on_transmission(ctx.user, msg, ctx.guild_id)
            return

        connected = check_if_connected(ctx.guild_id)

        if connected:
            await ctx.send('[ You are already transmitting! ]', ephemeral=True)
            return
        else:
            embed = await self.embed_manager('initial_connection')

            msg = await ctx.send(embeds=embed)

            await increment_value(ctx, 'times_transmitted', 1, ctx.user)

            connect_to_transmission(ctx.guild_id, ctx.channel_id)
            await self.on_transmission(ctx.user, msg, ctx.guild_id)
            return

    async def on_transmission(self, user: User, msg: Message, server_id: int):

        transmission = get_transmission(server_id)

        other_server: Guild

        if server_id == transmission.connection_a.server_id:
            other_server = await self.bot.fetch_guild(transmission.connection_b.server_id)
        else:
            other_server = await self.bot.fetch_guild(transmission.connection_a.server_id)

        server_data: ServerData = await ServerData(server_id).fetch()
        transmittable_servers = server_data.transmittable_servers
        transmittable_servers[str(other_server.id)] = other_server.name
        
        await server_data.update(transmittable_servers = transmittable_servers)

        btn_id = uuid.uuid4()

        disconnect = Button(
            style=ButtonStyle.DANGER,
            label='Disconnect',
            custom_id=str(btn_id)
        )

        async def check_button(component: Component):
            if user.id == component.ctx.user.id:
                return True
            else:
                await component.ctx.send(f'[ Only the initiator of this transmission ({User.mention}) can cancel it! ]',
                                ephemeral=True)
                return False

        task = asyncio.create_task(self.bot.wait_for_component(components=disconnect, check=check_button))

        disconnect_timer = 600

        embed = await self.embed_manager('connected')
        embed.description = f'[ Currently connected to **{other_server.name}**! ]'
        
        while connection_alive(server_id):
            done, _ = await asyncio.wait({task}, timeout=1)

            if not done:

                if disconnect_timer % 10 == 0:
                    time = humanfriendly.format_timespan(disconnect_timer)

                    embed.set_footer(text=f'Transmission will end in {time}.')

                    await msg.edit(embeds=embed, components=disconnect)

                disconnect_timer -= 1

                if disconnect_timer == 30:
                    await msg.reply('[ Transmission will end in 30 seconds. ]')

                if disconnect_timer == 0:
                    embed = await self.on_cancel('transmittime', id=server_id)

                    remove_connection(server_id)

                    await msg.edit(embeds=embed, components=[])
                    await msg.reply(embeds=embed)
                    return

                continue  # * Important

            embed = await self.on_cancel('manual', server_id, task.result().ctx)

            await msg.edit(embeds=embed, components=[])
            await msg.reply(embeds=embed)

            remove_connection(server_id)

            return

        embed = await self.on_cancel('server', id=server_id)
        
        remove_connection(server_id)

        await msg.edit(embeds=embed, components=[])
        await msg.reply(embeds=embed)

        return

    class TransmitUser:
        name: str
        id: int
        image: str

        def __init__(self, name, u_id, image):
            self.name = name
            self.id = u_id
            self.image = image

    async def check_anonymous(self, guild_id: int, d_user: User, connection: Connection, server_data: ServerData):

        user: TransmissionModule.TransmitUser

        if server_data.anonymous:
            
            i = 0
            
            selected_character = {}

            for i, character in enumerate(connection.characters):
                if character['id'] == 0 or character['id'] == d_user.id:
                    user = TransmissionModule.TransmitUser(character['Name'], d_user.id, f'https://cdn.discordapp.com/emojis/{character["Image"]}.png')

                    connection.characters[i].update({'id': d_user.id})
                    
                    selected_character = character

                    return user

            user = TransmissionModule.TransmitUser(selected_character['name'], d_user.id, selected_character['image'])
        else:
            user = TransmissionModule.TransmitUser(d_user.username, d_user.id, d_user.display_avatar.url)

        return user

    @listen()
    async def on_message_create(self, event: MessageCreate):

        message = event.message
        channel = message.channel
        guild = message.guild

        if channel.type == ChannelType.DM:
            return

        if message.author.id == 1015629604536463421 or message.author.id == 1028058097383641118:
            return
        
        if guild is None:
            return

        if connection_alive(guild.id):
            
            if message.author.id == self.bot.user.id:
                return
            
            server_data: ServerData = await ServerData(guild.id).fetch()
            
            transmission = get_transmission(guild.id)

            first_server = transmission.connection_a
            second_server = transmission.connection_b

            can_pass = False
            other_connection = None
            allow_images = True

            if first_server.channel_id == channel.id:
                can_pass = True
                user = await self.check_anonymous(guild.id, message.author, first_server, server_data)
                other_connection = await self.bot.fetch_channel(second_server.channel_id)
                allow_images = server_data.transmit_images

            if second_server.channel_id == channel.id:
                can_pass = True
                user = await self.check_anonymous(guild.id, message.author, second_server, server_data)
                other_connection = await self.bot.fetch_channel(first_server.channel_id)
                allow_images = server_data.transmit_images

            if can_pass:
                embed = await self.message_manager(message, user, allow_images)

                await other_connection.send(embeds=embed)

    async def message_manager(self, message: Message, user: TransmitUser, allow_images: bool):

        final_text = message.content

        embed = Embed(
            color=0x2b2d31,
            description=final_text
        )

        if len(message.attachments) > 0:
            image = message.attachments[0].url

            if '.mp4' in image or '.mov' in image:
                embed.video = EmbedAttachment(url=image)
                embed.set_footer('User sent a video, but discord does not allow bots to send videos in embeds.')
            elif allow_images:
                embed.image = EmbedAttachment(url=image)
            else:
                final_text += '\n\n[IMAGE]'

        embed.set_author(name=user.name, icon_url=user.image)

        embed.description = final_text

        return embed
                    
                    
    async def on_cancel(self, cancel_reason, id: int, button_ctx=None):

        if cancel_reason == 'timeout':
            return Embed(
                title='Transmission Cancelled.',
                description='Looks like no one wants to talk...',
                color=0xff1a1a
            )

        if cancel_reason == 'manual':
            return Embed(
                title='Transmission Cancelled.',
                description=f'{button_ctx.author.mention} cancelled the transmission.',
                color=0xff1a1a
            )

        if cancel_reason == 'server':
            return Embed(
                title='Transmission Cancelled.',
                description='The other server cancelled the transmission.',
                color=0xff1a1a
            )

        if cancel_reason == 'transmittime':
            return Embed(
                title='Transmission Ended.',
                description='You ran out of transmission time.',
                color=0xff1a1a
            )

    async def embed_manager(self, embed_type: str):
        if embed_type == 'initial_connection':
            return Embed(
                title='Transmission Starting!',
                description='Waiting for a connection... <a:loading:1026539890382483576>',
                color=0x933397
            )

        if embed_type == 'connected':
            return Embed(
                title='Connected!',
                color=0x47ff1a
            )


def setup(bot):
    TransmissionModule(bot)
