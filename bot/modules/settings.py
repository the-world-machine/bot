import json
from interactions import *

from utilities.database.main import ServerData
from utilities.message_decorations import fancy_message

# TODO: localelelele
class SettingsModule(Extension):
    
    @slash_command(description="Settings.")
    async def settings(self, ctx: SlashContext):
        pass

    server = settings.group(name="server")
    transmissions = settings.group(name="transmissions")

    async def check(self, ctx: SlashContext):

        if Permissions.MANAGE_GUILD not in ctx.member.guild_permissions:
            await ctx.send("[ You do not have the permissions to use this command. ]", ephemeral=True)
            return False

        return True

    @transmissions.subcommand(
        sub_cmd_description="The transmission channel to use to allow other servers to call. Leave blank to disable."
    )
    @slash_option(
        description="DEFAULT: NO CHANNEL SET",
        name="channel",
        opt_type=OptionType.CHANNEL,
    )
    async def transmit_channel(self, ctx: SlashContext, channel: GuildText):
        
        if not await self.check(ctx):
            return

        server_data = await ServerData(ctx.guild_id).fetch()

        if channel is None:
            await server_data.update(transmit_channel=None)
            return await fancy_message(
                ctx, "[ Successfully disabled transmission calls. ]", ephemeral=True
            )

        await server_data.update(transmit_channel=str(channel.id))
        return await fancy_message(
            ctx,
            f"[ Successfully allowed other servers to call to {channel.mention}. ]",
            ephemeral=True,
        )

    @transmissions.subcommand(
        sub_cmd_description="Disable/Enable receiving images when transmitting. All redacted images will be sent as [IMAGE]."
    )
    @slash_option(
        description="DEFAULT: TRUE",
        name="value",
        opt_type=OptionType.BOOLEAN,
        required=True,
    )
    async def transmit_images(self, ctx: SlashContext, value):
        
        if not await self.check(ctx):
            return

        server_data = await ServerData(ctx.guild_id).fetch()

        await server_data.update(transmit_images=value)

        if value:
            return await fancy_message(
                ctx, "[ Successfully enabled transmission images. ]", ephemeral=True
            )
        else:
            return await fancy_message(
                ctx, "[ Successfully disabled transmission images. ]", ephemeral=True
            )

    @transmissions.subcommand(
        sub_cmd_description="Disable/Enable whether transmission receivers are shown Oneshot characters instead of users."
    )
    @slash_option(
        description="DEFAULT: FALSE",
        name="value",
        opt_type=OptionType.BOOLEAN,
        required=True,
    )
    async def transmit_anonymous(self, ctx: SlashContext, value):
        
        if not await self.check(ctx):
            return

        server_data = await ServerData(ctx.guild_id).fetch()

        await server_data.update(transmit_anonymous=value)

        if value:
            return await fancy_message(
                ctx, "[ Successfully enabled anonymous mode. ]", ephemeral=True
            )
        else:
            return await fancy_message(
                ctx, "[ Successfully disabled anonymous mode. ]", ephemeral=True
            )

    @transmissions.subcommand(
        sub_cmd_description="Block a server from being able to call."
    )
    @slash_option(
        description="Server to block.",
        name="server",
        opt_type=OptionType.STRING,
        required=True,
        autocomplete=True,
    )
    async def block_server(self, ctx: SlashContext, server: str):
        
        if not await self.check(ctx):
            return

        server_data: ServerData = await ServerData(ctx.guild_id).fetch()

        block_list = server_data.blocked_servers

        try:
            server_id = int(server)
        except ValueError:
            return await fancy_message(ctx, "[ Invalid server ID. ]", ephemeral=True)

        if server_id in block_list:
            block_list.remove(server_id)

            await server_data.update(blocked_servers=block_list)

            return await fancy_message(
                ctx, f"[ Successfully unblocked server `{server}`. ]", ephemeral=True
            )

        block_list.append(server_id)

        await server_data.update(blocked_servers=block_list)
        return await fancy_message(
            ctx, f"[ Successfully blocked server `{server}`. ]", ephemeral=True
        )

    @block_server.autocomplete("server")
    async def block_server_autocomplete(self, ctx: AutocompleteContext):

        server_data: ServerData = await ServerData(ctx.guild_id).fetch()

        transmitted_servers = server_data.transmittable_servers

        server = ctx.input_text

        servers = []

        for server_id, server_name in transmitted_servers.items():

            if not server:
                servers.append({"name": server_name, "value": server_id})
                continue

            if server.lower() in server_name.lower():
                servers.append({"name": server_name, "value": server_id})

        await ctx.send(servers)

    @server.subcommand()
    async def welcome_message(self, ctx: SlashContext):
        "Edit this server's welcome message."

        modal = Modal(
            InputText(
                label="Edit Welcome Message",
                style=TextStyles.PARAGRAPH,
                custom_id="message",
                placeholder="- [user] for the member's username.\n- [server] for the server's name.\n\nLeave blank to disable.",
                max_length=150,
                required=False,
            ),
            title="Welcome Message Editor",
            custom_id="welcome_message_editor",
        )

        await ctx.send_modal(modal)

    @modal_callback("welcome_message_editor")
    async def welcome_message_editor(self, ctx: ModalContext, message: str):

        server_data: ServerData = await ServerData(ctx.guild_id).fetch()
        await server_data.update(welcome_message=message)

        await ctx.send(
            f"Successfully updated welcome message to: ```{message}```", ephemeral=True
        )
