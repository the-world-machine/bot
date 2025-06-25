import random
import re

from interactions import *
from utilities.message_decorations import *
from utilities.localization import Localization, assign_variables


class InteractCommands(Extension):

	@slash_command(description="Interact with others in various ways (sends a message in chat)")
	@slash_option(
	    name='with',
	    description='The person you want to interact with',
	    opt_type=OptionType.USER,
	    required=True,
	    argument_name="user"
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def interaction(self, ctx: SlashContext, user: User):
		await self.start_interaction(ctx, user)

	@user_context_menu('💡 Interact...')
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def interaction_context(self, ctx: ContextMenuContext):
		await self.start_interaction(ctx, ctx.target)

	async def start_interaction(self, ctx: SlashContext, who: User):
		loc = Localization(ctx.locale)
		await fancy_message(ctx, loc.l('nikogotchi.loading'))

		if ctx.author.id == who.id:
			return await fancy_message(
			    ctx,
			    loc.l('interact.twm_is_fed_up_with_you', user=ctx.author.mention),
			    ephemeral=True,
			    color=Colors.BAD
			)
		"""if who.id == ctx.client.user.id:
			return await fancy_message(
			    ctx,
			    loc.l('interact.twm_not_being_very_happy', user=ctx.author.mention),
			    ephemeral=True,
			    color=0XFF0000
			)
		if who.bot:
            await fancy_message(ctx, loc.l('interact.twm_questioning_if_youre_stupid_or_not', bot=who.mention, user=ctx.author.mention), ephemeral=True, color=0XFF0000)
            return"""

		await ctx.send(content=loc.l('interact.selected', user=who.mention), components=[], ephemeral=True)

	handle_components_regex = re.compile(r"interact (?P<user_one>.+) (?P<user_two>.+) (?P<path>.+)$")

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		match = self.handle_components_regex.match(ctx.custom_id)
		if not match:
			return
		if len(match.groups()) <= 3:
			return ctx.edit_origin()
		user_one, user_two, path = match.group("user_one", "user_two", "path")

		if isinstance(text, tuple):
			text = random.choice(text)
		try:
			await ctx.channel.send(
			    assign_variables(text, locale=ctx.locale, user_one=ctx.author.mention, user_two=user.mention)
			)
		except:
			pass

	@component_callback('interaction_selected')
	async def menu_callback(self, ctx: ComponentContext):
		if ctx.message:
			return await ctx.message.delete()
		loc = Localization(ctx.locale)
		await ctx.defer(edit_origin=True)

		args = ctx.values[0].split('_')
		user = ctx.client.get_user(args[1])
		text = loc.l(f'interact.options.{args[0]}.messages')
		if isinstance(text, tuple):
			text = random.choice(text)

		await ctx.channel.send(
		    assign_variables(text, locale=ctx.locale, user_one=ctx.author.mention, user_two=user.mention)
		)
