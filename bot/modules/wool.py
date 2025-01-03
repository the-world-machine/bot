import random
import asyncio
from interactions import *
from utilities.emojis import emojis
from datetime import datetime, timedelta
from utilities.database.main import UserData
from utilities.localization import Localization, fnum
from utilities.message_decorations import Colors, fancy_message

wool_finds = [{
    'message': 'and they despise you today... Too bad...',
    'amount': 'negative_major',
    'chance': 70
}, {
    'message': 'and they\'re happy with you! Praise be The World Machine!',
    'amount': 'positive_normal',
    'chance': 30
}, {
    'message':
        "and they see you're truly a devoted follower. Praise be The World Machine!",
    'amount':
        'positive_major',
    'chance':
        5
}, {
    'message': 'but they saw your misdeed the other day.',
    'amount': 'negative_minimum',
    'chance': 40
}, {
    'message': "but they aren't happy with you today.",
    'amount': 'negative_normal',
    'chance': 20
}, {
    'message': 'and they see you\'re doing okay.',
    'amount': 'positive_minimum',
    'chance': 100
}]

wool_values = {
    'positive_minimum': [500, 3000],
    'positive_normal': [1000, 3_000],
    'positive_major': [10_000, 50_000],
    'negative_minimum': [-10, -50],
    'negative_normal': [-100, -300],
    'negative_major': [-500, -1000]
}


class WoolModule(Extension):

	@slash_command(description='All things to do with wool')
	async def wool(self, ctx: SlashContext):
		pass

	@wool.subcommand(sub_cmd_description='View your balance')
	@slash_option(description='The person you want to view balance of instead',
	              name='of',
	              opt_type=OptionType.USER)
	async def balance(self, ctx: SlashContext, of: User = None):
		if of is None:
			of = ctx.user

		user_data: UserData = await UserData(of.id).fetch()
		wool: int = user_data.wool
		if of.bot:
			if of == ctx.client.user:
				if wool <= 0:
					return await fancy_message(
					    ctx,
					    f"[ I try not to influence the economy, so i have **no{emojis['icons']['wool']}Wool** ]"
					)
				else:
					return await fancy_message(
					    ctx,
					    f"[ I try not to influence the economy, but i was given {emojis['icons']['wool']}**{fnum(wool)}** ]"
					)
			if wool == 0:
				return await fancy_message(
				    ctx,
				    f"[ Bots usually don't interact with The World Machine, not that they even can...\n"
				    +
				    f"So {of.mention} has no {emojis['icons']['wool']}**Wool** ]"
				)
			else:
				return await fancy_message(
				    ctx,
				    f"[ Bots usually don't interact with The World Machine, not that they even can...\n"
				    +
				    f"But, {of.mention} was given {emojis['icons']['wool']}**{fnum(wool)}** ]"
				)
		if wool == 0:
			await fancy_message(
			    ctx,
			    f"[ **{of.mention}** has no **Wool**{emojis['icons']['wool']}. ]",
			)
		else:
			await fancy_message(
			    ctx,
			    f"[ **{of.mention}** has {emojis['icons']['wool']}**{fnum(wool)}**. ]",
			)

	@wool.subcommand(sub_cmd_description='Give away some of your wool')
	@slash_option(description='Who would you like to give?',
	              name='to',
	              required=True,
	              opt_type=OptionType.USER)
	@slash_option(description='How much wool would you like to give them?',
	              name='amount',
	              required=True,
	              opt_type=OptionType.INTEGER,
	              min_value=-1)
	async def give(self, ctx: SlashContext, to: User, amount: int):
		loc = Localization(ctx.locale)
		if to.id == ctx.author.id:
			return await fancy_message(ctx,
			                           '[ What... ]',
			                           ephemeral=True,
			                           color=Colors.BAD)

		if to.bot and not (amount <= 0):
			buttons = [
			    Button(style=ButtonStyle.RED,
			           label=loc.l('general.buttons._yes'),
			           custom_id=f'yes'),
			    Button(style=ButtonStyle.GRAY,
			           label=loc.l('general.buttons._no'),
			           custom_id=f'no')
			]

			confirmation_m = await fancy_message(
			    ctx,
			    message=
			    "[ Are you sure you want to give wool... to a bot? You won't be able get it back, you know... ]",
			    color=Colors.WARN,
			    components=buttons,
			    ephemeral=True)
			try:
				await ctx.client.wait_for_component(messages=confirmation_m,
				                                    timeout=60.0 * 1000)
				await ctx.delete(confirmation_m)
			except asyncio.TimeoutError:
				await confirmation_m.edit(
				    content="[ You took too long to respond ]", components=[])
				await ctx.delete()
				await asyncio.sleep(15)
				await confirmation_m.delete()

		loading = await fancy_message(ctx, loc.l('general.loading'))
		from_user: UserData = await UserData(ctx.author.id).fetch()
		to_user: UserData = await UserData(to.id).fetch()

		if from_user.wool < amount:
			return await fancy_message(
			    ctx,
			    f"[ You don't have that much wool! (you have only {from_user.wool}) ]",
			    edit=True,
			    ephemeral=True,
			    color=Colors.BAD)

		await from_user.manage_wool(-amount)
		await to_user.manage_wool(amount)

		if amount > 0:
			if ctx.user.bot:
				await fancy_message(
				    loading,
				    f"{ctx.author.mention} gave away {emojis['icons']['wool']}**{fnum(amount)}** to {to.mention}, how generous...",
				    edit=True)
			else:
				await fancy_message(
				    loading,
				    f"{ctx.author.mention} gave away {emojis['icons']['wool']}**{fnum(amount)}** to {to.mention}, how generous!",
				    edit=True)
		elif amount == 0:
			if ctx.user.bot:
				await fancy_message(
				    loading,
				    f"{ctx.author.mention} gave away {emojis['icons']['wool']}**{fnum(amount)}** to {to.mention}, not very generous!",
				    edit=True)
			else:
				await fancy_message(
				    loading,
				    f"{ctx.author.mention} gave away {emojis['icons']['wool']}**{fnum(amount)}** to {to.mention}, not very generous after all...",
				    edit=True)
		else:
			await fancy_message(
			    loading,
			    f"{ctx.author.mention} stole a single piece of wool from {to.mention}, why!?",
			    edit=True)

	@wool.subcommand()
	async def daily(self, ctx: SlashContext):
		'''This command has been renamed to /pray'''

		await self.pray(ctx)

	@slash_command()
	async def pray(self, ctx: SlashContext):
		'''Pray to The World Machine'''

		user_data: UserData = await UserData(ctx.author.id).fetch()
		last_reset_time = user_data.daily_wool_timestamp

		now = datetime.now()

		if now < last_reset_time:
			time_unix = last_reset_time.timestamp()
			return await fancy_message(
			    ctx,
			    f"[ You've already prayed in the past 24 hours. You can pray again <t:{int(time_unix)}:R>. ]",
			    ephemeral=True,
			    color=Colors.BAD)

		# reset the limit if it is a new day
		if now >= last_reset_time:
			reset_time = datetime.combine(now.date(),
			                              now.time()) + timedelta(days=1)
			await user_data.update(daily_wool_timestamp=reset_time)

		random.shuffle(wool_finds)

		response = wool_finds[0]

		number = random.randint(0, 100)

		amount = 0
		message = ''

		for wool_find in wool_finds:
			if number <= wool_find['chance']:
				amount = wool_find['amount']
				message = wool_find['message']
				break

		response = f'You prayed to The World Machine...'

		amount = wool_values[amount]
		amount = int(random.uniform(amount[0], amount[1]))

		if amount > 0:
			value = f"You got {fnum(amount)} wool!"
			color = Colors.GREEN
		else:
			value = f"You lost {fnum(abs(amount))} wool..."
			color = Colors.BAD

		await user_data.update(wool=user_data.wool + amount)

		await ctx.send(embed=Embed(title='Pray',
		                           description=f'{response}\n{message}',
		                           footer=EmbedFooter(text=value),
		                           color=color))

	@wool.subcommand()
	@slash_option(description='How much wool would you like to bet?',
	              name='bet',
	              required=True,
	              opt_type=OptionType.INTEGER,
	              min_value=100)
	async def gamble(self, ctx: SlashContext, bet: int):
		"""Moved to /gamble wool"""
		from modules.gamble import GambleModule
		return await GambleModule.wool(ctx, ctx, bet)
