import re
import random
import asyncio
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
		await fancy_message(ctx, Localization(ctx.locale).l('general.loading'), ephemeral=True)

		return await self.respond(ctx, str(who.id), "main")
		"""if ctx.author.id == who.id:
			return await fancy_message(
			    ctx,
			    Localization(ctx.locale).l('interact.twm_is_fed_up_with_you', user=ctx.author.mention),
			    ephemeral=True,
			    color=0XFF0000
			)
		if who.id == ctx.client.user.id:
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

	handle_components_regex = re.compile(r"interact (?P<user_two>.+) (?P<path>.+)$")

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		await fancy_message(ctx, Localization(ctx.locale).l('general.loading'), ephemeral=True, edit_origin=True)
		match = self.handle_components_regex.match(ctx.custom_id)
		user_two, path = match.group("user_two", "path")
		return await self.respond(ctx, user_two, path)

	@staticmethod
	def fat_condition(messages):
		return (isinstance(messages, tuple) and all(isinstance(msg, dict) for msg in messages) and len(messages) > 1)

	async def respond(self, ctx: ComponentContext | SlashContext, user_two: str, path: str):
		loc = Localization(ctx.locale)
		#                                       \/ this returns ['',''] if path is "main"
		messages = loc.l(f'interact.options{path.split("main")[1]}')
		if isinstance(messages, str) and messages.startswith("`"):
			return await ctx.edit()
		
		if isinstance(messages, tuple) and len(messages) == 1 and isinstance(messages[0], dict) and all(
		    isinstance(msg, str) for msg in messages[0]['messages']
		):
			messages = messages[0]
			# this has GOT to have an easier way
		if (isinstance(messages, tuple) and all(isinstance(msg, str) for msg in messages)) or (
		    isinstance(messages, dict) and all(isinstance(msg, str) for msg in messages['messages'])
		    and len(messages) > 1
		):
			try:
				user_two = (await ctx.client.fetch_user(user_two)).mention
			except:
				user_two = f"<@{user_two}>"

			if isinstance(messages, dict):
				messages = messages['messages']
			message = assign_variables(
			    random.choice(messages), locale=ctx.locale, user_one=ctx.author.mention, user_two=user_two
			)
			try:
				msg = await ctx.channel.send(content=message)
			except:
				msg = await ctx.send(content=message, ephemeral=False)

			if user_two == ctx.client.user.mention:
				await asyncio.sleep(random.choice([2, 1.5, 0.5, 0]))
				await msg.add_reaction("1023573456664662066")
		else:
			buttons = sorted([
				Button(
					custom_id=f"interact {user_two} {path}[{i}].messages",
					style=ButtonStyle.GRAY,
					label=messages[i]['name'],
					emoji="🔢" if self.fat_condition(messages[i]['messages']) else None
				) for i in range(len(messages))
			], key=lambda button: ((button.emoji.name != "🔢" if button.emoji is not None else True), button.label))
			# TODO: paging
			if len(buttons) > 15:
				return "go nuclear"
			rows = [ActionRow(*buttons[i:i + 5]) for i in range(0, len(buttons), 5)]
			if path != 'main':
				this = loc.l(f"interact.options{path.split("main")[1].rsplit(".", 1)[0]}")
				rows += [
				    ActionRow(
				        Button(
				            label=loc.l("general.buttons._back"),
				            custom_id=f"interact {user_two} {path.rsplit("[", 1)[0] if path.rsplit("[", 1)[0] != "main" else "main"}",
				            style=ButtonStyle.BLURPLE,
				        ),
				        Button(
				            label=this['name'],
				            disabled=True,
				            custom_id=f"unused",
				            style=ButtonStyle.GRAY,
				        )
				    ),
				]
			try:
				user_two = (await ctx.client.fetch_user(user_two)).mention
			except:
				user_two = f"<@{user_two}>"
			await ctx.edit(
			    embed=Embed(description=loc.l('interact.selected', user=user_two), color=Colors.DEFAULT),
			    components=rows
			)

	@component_callback('interaction_selected')
	async def menu_callback(self, ctx: ComponentContext):  # the
		await ctx.message.delete()
