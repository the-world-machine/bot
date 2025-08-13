import time
from utilities.config import debugging
from datetime import datetime, timedelta
from utilities.message_decorations import *
import utilities.profile.badge_manager as bm
from utilities.profile.main import draw_profile
from utilities.database.schemas import UserData
from utilities.localization import Localization, fnum
from interactions import Button, ButtonStyle, Extension, Member, OptionType, SlashCommandChoice, SlashContext, User, contexts, integration_types, slash_command, slash_option


class ProfileCommands(Extension):

	@slash_command(description='All things to do with profiles')
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def profile(self, ctx):
		pass

	@slash_command(description='All things to do with Suns')
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def sun(self, ctx):
		pass

	@sun.subcommand(sub_cmd_description='Give someone a sun!')
	@slash_option(description='Person to give the sun to', name='who', opt_type=OptionType.USER, required=True)
	async def give(self, ctx: SlashContext, who: User):
		user_data: UserData = await UserData(_id=who.id).fetch()

		if who.bot:
			return await fancy_message(ctx, "[ Bot's can't receive suns! ]", color=Colors.BAD, ephemeral=True)

		if who.id == ctx.author.id:
			return await fancy_message(ctx, "[ Nuh uh! ]", color=Colors.BAD, ephemeral=True)

		now = datetime.now()

		last_reset_time = user_data.daily_sun_timestamp

		if now < last_reset_time:
			time_unix = last_reset_time.timestamp()
			return await fancy_message(
			    ctx,
			    f"[ You've already given a sun to someone! You can give one again <t:{int(time_unix)}:R>. ]",
			    ephemeral=True,
			    color=Colors.BAD
			)

		# reset the limit if it is a new day
		if now >= last_reset_time:
			reset_time = now + timedelta(days=1)
			await user_data.update(daily_sun_timestamp=reset_time)
		_ = ctx.author
		if isinstance(_, Member):
			_ = _.user
		await bm.increment_value(ctx, 'suns', target=_)  # TODO: is it supposed to give suns to both?
		await bm.increment_value(ctx, 'suns', target=who)

		await ctx.send(f"[ {ctx.author.mention} gave {who.mention} a sun! {emojis['icons']['sun']} ]")

	@profile.subcommand(sub_cmd_description='View a profile')
	@slash_option(description="Person you want to see the profile of", name='user', opt_type=OptionType.USER)
	async def view(self, ctx: SlashContext, user: User | None = None):
		url = "https://theworldmachine.xyz/profile"

		loc = Localization(ctx)
		if user is None:
			user = ctx.user
		if user.bot and ctx.client.user != user:
			return await ctx.send(loc.l("profile.view.bots"), ephemeral=True)

		await fancy_message(ctx, loc.l("profile.view.loading", user=user.mention))

		start_time = time.perf_counter()
		image = await draw_profile(user, filename=loc.l("profile.view.image.name", username=user.id), loc=loc)
		runtime = (time.perf_counter() - start_time) * 1000
		components = []
		if user == ctx.user:
			components.append(
			    Button(
			        style=ButtonStyle.URL,
			        url=url,
			        label=loc.l("profile.view.BBBBBUUUUUTTTTTTTTTTOOOOONNNNN"),
			    )
			)
		content = loc.l("profile.view.message", usermention=user.mention)
		await ctx.edit(
		    content=f"-# Took {fnum(runtime, locale=loc.locale)}ms. {content}" if debugging() else f"-# {content}",
		    files=image,
		    components=components,
		    allowed_mentions={ 'users': []},
		    embeds=[]
		)

	@profile.subcommand(sub_cmd_description='Edit your profile')
	async def edit(self, ctx: SlashContext):
		components = Button(
		    style=ButtonStyle.URL,
		    label=Localization(ctx).l('generic.buttons.open_site'),
		    url="https://theworldmachine.xyz/profile"
		)
		await fancy_message(
		    ctx, message=Localization(ctx).l('profile.edit.text'), ephemeral=True, components=components
		)

	choices = [
	    SlashCommandChoice(name='Sun Amount', value='suns'),
	    SlashCommandChoice(name='Wool Amount', value='wool'),
	    SlashCommandChoice(name='Times Shattered', value='times_shattered'),
	    SlashCommandChoice(name='Times Asked', value='times_asked'),
	    SlashCommandChoice(name='Times Messaged', value='times_messaged'),
	    SlashCommandChoice(name='Times Transmitted', value='times_transmitted')
	]                                                                           # TODO: what is this
