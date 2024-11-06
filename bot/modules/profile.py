import json
import os
from datetime import datetime, timedelta

import aiofiles
from interactions import Extension, SlashContext, User, OptionType, slash_command, slash_option, SlashCommandChoice, Button, ButtonStyle, File

import utilities.profile.badge_manager as bm
import utilities.profile.profile_viewer as profile_viewer
import database as db
from utilities.message_decorations import *


class ProfileModule(Extension):

    async def open_backgrounds(self):
        async with aiofiles.open('bot/data/backgrounds.json', 'r') as f:
            strdata = await f.read()

        return json.loads(strdata)

    @slash_command(description='All things to do with profiles.')
    async def profile(self, ctx):
        pass

    @slash_command(description='All things to do with Suns.')
    async def sun(self, ctx):
        pass

    @sun.subcommand(sub_cmd_description='Give someone a sun!')
    @slash_option(description='Person to give the sun to', name='who', opt_type=OptionType.USER, required=True)
    async def give(self, ctx: SlashContext, user: User):
        
        user_data: db.UserData = await db.UserData(user.id).fetch()

        if user.bot:
            await fancy_message(ctx, "[ Can't send bots suns! ]", color=0xFF0000, ephemeral=True)
            return

        if user.id == ctx.author.id:
            await fancy_message(ctx, "[ Can't give yourself a sun! ]", color=0xFF0000, ephemeral=True)
            return
                
        now = datetime.now()
        
        last_reset_time = user_data.daily_sun_timestamp

        if now < last_reset_time:
            time_unix = last_reset_time.timestamp()
            return await fancy_message(ctx, f"[ You've already given a sun to someone! You can give one again <t:{int(time_unix)}:R>. ]", ephemeral=True, color=0xFF0000)

        # reset the limit if it is a new day
        if now >= last_reset_time:
            reset_time = now + timedelta(days=1)
            await user_data.update(daily_sun_timestamp=reset_time)

        await bm.increment_value(ctx, 'suns', target=ctx.author)
        await bm.increment_value(ctx, 'suns', target=user)

        await ctx.send(f'[ {ctx.author.mention} gave {user.mention} a sun! <:Sun:1026207773559619644> ]')
        
    @profile.subcommand(sub_cmd_description='View a profile.')
    @slash_option(description='The user\'s profile to view.', name='user', opt_type=OptionType.USER, required=True)
    async def view(self, ctx: SlashContext, user: User):

        if user.bot:
            return await ctx.send('[ Cannot view profiles of bots. ]', ephemeral=True)

        msg = f'[ Loading {user.username}\'s profile... <a:loading:1026539890382483576> ]'

        message = await fancy_message(ctx, msg)

        await profile_viewer.draw_badges(user)
        
        button = Button(
            style=ButtonStyle.URL,
            url=f'https://www.theworldmachine.xyz/profile',
            label='Edit Profile',
        )

        img_ = File('bot/images/profile_viewer/result.png', description=f'{user.username}\'s profile.')

        await message.edit(components=button, content='', embed=[], files=img_)

        os.remove('bot/images/profile_viewer/result.png')

    choices = [
        SlashCommandChoice(name='Sun Amount', value='suns'),
        SlashCommandChoice(name='Wool Amount', value='wool'),
        SlashCommandChoice(name='Times Shattered', value='times_shattered'),
        SlashCommandChoice(name='Times Asked', value='times_asked'),
        SlashCommandChoice(name='Times Messaged', value='times_messaged'),
        SlashCommandChoice(name='Times Transmitted', value='times_transmitted')
    ]
