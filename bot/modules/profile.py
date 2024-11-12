import json
import os
from datetime import datetime, timedelta

import aiofiles
from interactions import Extension, SlashContext, User, OptionType, slash_command, slash_option, SlashCommandChoice, Button, ButtonStyle, File

from utilities.localization import Localization
import utilities.profile.badge_manager as bm
from utilities.profile.main import draw_profile
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
            return await fancy_message(ctx, "[ Bot's can't receive suns! ]", color=0xFF0000, ephemeral=True)

        if user.id == ctx.author.id:
            return await fancy_message(ctx, "[ Nuh uh! ]", color=0xFF0000, ephemeral=True)
                
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
    @slash_option(description="Would you like to see someone else's profile?", name='user', opt_type=OptionType.USER)
    async def view(self, ctx: SlashContext, user: User = None):
        loc = Localization(ctx.locale)
        if user is None:
            user = ctx.user
        url = "https://theworldmachine.xyz/profile"
        if user.bot:
            return await ctx.send(loc.l("profile.view.bot"), ephemeral=True)

        message = await fancy_message(ctx, loc.l("profile.view.loading", user=user.mention))

        image = await draw_profile(user,
                                                 filename=loc.l("profile.view.image.name", username=user.id),
                                                 description=loc.l("profile.view.image.title", username=user.username),
                                                 locale=ctx.locale)
        
        components = []
        if user == ctx.user:
            components.append(Button(
                style=ButtonStyle.URL,
                url=url,
                label=loc.l("profile.view.BBBBBUUUUUTTTTTTTTTTOOOOONNNNN"),
            ))

        await message.edit(files=image, components=components, content='', embeds=[])

    @profile.subcommand(sub_cmd_description='Edit your profile.')
    async def profile(self, ctx: SlashContext):
        components = Button(
            style=ButtonStyle.URL,
            label=Localization.sl('general.buttons._open_site', locale=ctx.locale),
            url="https://theworldmachine.xyz/profile"
        )
        await fancy_message(ctx, message=Localization.sl('profile.edit', locale=ctx.locale), ephemeral=True, components=components)
        
    choices = [
        SlashCommandChoice(name='Sun Amount', value='suns'),
        SlashCommandChoice(name='Wool Amount', value='wool'),
        SlashCommandChoice(name='Times Shattered', value='times_shattered'),
        SlashCommandChoice(name='Times Asked', value='times_asked'),
        SlashCommandChoice(name='Times Messaged', value='times_messaged'),
        SlashCommandChoice(name='Times Transmitted', value='times_transmitted')
    ]
