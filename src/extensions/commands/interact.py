from __future__ import annotations
import asyncio
from dataclasses import dataclass
import random
import re
from typing import Any
from interactions import ActionRow, Button, ButtonStyle, ComponentContext, ContextMenuContext, Embed, Extension, Member, MentionType, Message, OptionType, SlashContext, Snowflake_Type, User, component_callback, contexts, integration_types, message_context_menu, slash_command, slash_option, user_context_menu, AllowedMentions
from utilities.emojis import emojis
from utilities.localization import Localization
from utilities.message_decorations import fancy_message


@dataclass(frozen=True)
class InteractionEntry:
	name: str
	messages: tuple[InteractionEntry | str]


class InteractCommands(Extension):

	@user_context_menu('💡 interact...')
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def user_context(self, ctx: ContextMenuContext):
		who = ctx.target
		assert isinstance(who, (Member, User)), "hi linter"
		if isinstance(who, Member):
			who = who.user

		invoker = ctx.author
		if isinstance(invoker, Member):
			invoker = invoker.user
		return await self.start(ctx, invoker, who)

	@message_context_menu('💡 interact w/sender...')
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def message_context(self, ctx: ContextMenuContext):
		assert isinstance(ctx.target, Message), "hi linter"
		who = ctx.target.author
		if isinstance(who, Member):
			who = who.user

		invoker = ctx.author
		if isinstance(invoker, Member):
			invoker = invoker.user
		return await self.start(ctx, invoker, who)

	@slash_command(name="interact", description="Interact with others in various ways (sends a message in chat)")
	@slash_option(
	    name='with',
	    description="The interactee (can be @, won't ping everyone/here/roles though)",
	    opt_type=OptionType.STRING,
	    required=True,
	    max_length=128,
	    argument_name="user_two"
	)
	@slash_option(
	    name='user_one',
	    description="Optional replacement for the first user (same as interactee, but message won't ping anyone)",
	    opt_type=OptionType.STRING,
	    max_length=128,
	    argument_name="user_one"
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def slash_context(self, ctx: SlashContext, user_two: str | User, user_one: str | User | None = None):
		user_one, user_two = await self.parse_args(ctx, user_one, user_two)
		return await self.start(ctx, user_one, user_two)

	##### ↓ Bot side ↓ #####

	async def parse_args(self, ctx: SlashContext | ComponentContext, user_one: str | User | None,
	                     user_two: str | User) -> tuple[str | User, str | User]:
		if user_one:
			try:
				assert isinstance(
				    user_one, str
				), "meow"  # this is to use user_one/two as the variables to send to self.start instead of creating new one's (this function (slash_context) will never trigger with User objects in arguments)
				_user = await ctx.client.fetch_user(user_one.strip("<@>"))
				if _user:
					user_one = _user
			except:
				...
			_user = None
		else:
			_ = ctx.author
			if isinstance(_, Member):
				_ = _.user
			user_one = _

		try:
			assert isinstance(user_two, str), "meow"
			_user = await ctx.client.fetch_user(user_two.strip("<@>"))
			if _user:
				user_two = _user
		except:
			...
		return (user_one, user_two)

	async def start(self, ctx: ContextMenuContext | SlashContext, user_one: str | User, user_two: str | User):
		loc = Localization(ctx.locale)
		await fancy_message(ctx, loc.l('general.loading'), ephemeral=True)
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
            return
								await fancy_message(
		    ctx,
		    message=loc.l(
		        f'interact.selected{"_self" if with_self else ""}',
		        user_one=f"<@{user_one.id}>" if isinstance(user_one, User) else user_one,
		        user_two=f"<@{user_two.id}>" if isinstance(user_two, User) else user_two
		    ),
		    components=[
		        Button(
		            label="Delicate Boop",
		            custom_id=f"interact {ctx.id} [0].phrases[2].phrases",
		            style=ButtonStyle.GRAY,
		        )
		    ],
		    edit=True
		)
		"""
		return await self.respond((ctx, loc), (0, "", user_one, user_two))

	handle_components_regex = re.compile(r"interact (?P<page>.+) (?P<path>.+)$")

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		loc = Localization(ctx.locale)
		assert ctx.message is not None, "discorded"
		newcontent = ctx.message.content.replace("❔", emojis['icons']['loading'])
		await ctx.edit_origin(content=newcontent)
		try:
			stuff = ctx.message.content.split("→")  # type:ignore
		except:
			return
		match = self.handle_components_regex.match(ctx.custom_id)
		if match:
			page, path = match.group("page", "path")
		assert isinstance(page, str) and isinstance(path, str)

		user_one = stuff[0][3:-1]
		user_two = stuff[2].strip()
		user_one, user_two = await self.parse_args(ctx, user_one, user_two)

		message = loc.l(f"interact.options{path}", typecheck=Any)
		if isinstance(message, tuple):
			return await self.send_phrase((ctx, loc), (path, user_one, user_two))
		return await self.respond((ctx, loc), (int(page), path, user_one, user_two))

	@staticmethod
	def ie_includes_more(messages: tuple):  # interaction entry includes more interaction entries (nested)
		return (isinstance(messages, tuple) and all(isinstance(msg, dict) for msg in messages) and len(messages) > 1)

	async def respond(
	    self, cx: tuple[ComponentContext | ContextMenuContext | SlashContext, Localization],
	    state: tuple[int, str, str | User, str | User]
	):
		ctx, loc = cx
		page, path, user_one, user_two = state
		messages = loc.l(f"interact.options{path}", typecheck=Any)

		all_buttons: list[Button] = sorted(
		    [
		        Button(
		            custom_id=f"interact {page} {path}[{i}]"
		            if self.ie_includes_more(messages[i]['phrases']) else f"interact {page} {path}[{i}].phrases",
		            style=ButtonStyle.GRAY,
		            label=messages[i]['name'],
		            emoji="🔢" if self.ie_includes_more(messages[i]['phrases']) else None
		        ) for i in range(len(messages))
		    ],
		    key=lambda button: ((button.emoji.name != "🔢" if button.emoji is not None else True), button.label)
		)
		buttons: list[Button] = []
		if path != "":
			buttons.append(Button(
			    label=messages['name'],
			    disabled=True,
			    custom_id=f"unused",
			    style=ButtonStyle.GRAY,
			))

		buttons_per_page = 24
		paging = len(all_buttons) > buttons_per_page
		if paging:
			buttons_per_page -= 1  # next button
			if page > 0 and page < len(all_buttons) / buttons_per_page:
				buttons_per_page -= 1  # prev button
		buttons.extend(all_buttons[page:page + 1 + buttons_per_page])
		if paging and page > 0:
			buttons.insert(0, Button(custom_id=f"interact {page-1} {path}", style=ButtonStyle.BLURPLE, emoji="⬅️"))
		if paging and page < len(all_buttons) / buttons_per_page:
			buttons.insert(0, Button(custom_id=f"interact {page+1} {path}", style=ButtonStyle.BLURPLE, emoji="⬅️"))

		rows = [ActionRow(*buttons[i:i + 5]) for i in range(0, len(buttons), 5)]
		return await ctx.edit(
		    content=
		    f"-# {f'<@{user_one.id}>' if isinstance(user_one, User) else user_one} → ❔ → {f'<@{user_two.id}>' if isinstance(user_two, User) else user_two}",
		    embeds=[],
		    components=rows,
		    allowed_mentions=AllowedMentions(parse=[])
		)

	async def send_phrase(
	    self, cx: tuple[ComponentContext | ContextMenuContext | SlashContext, Localization],
	    state: tuple[str, str | User, str | User]
	):
		ctx, loc = cx
		quote_path, user_one, user_two = state

		phrases: tuple[str] = loc.l(
		    f"interact.options{quote_path}",
		    typecheck=tuple,
		    user_one=f"<@{user_one.id}>" if isinstance(user_one, User) else user_one,
		    user_two=f"<@{user_two.id}>" if isinstance(user_two, User) else user_two
		)
		assert isinstance(phrases, tuple), "Phrase path does not lead to a tuple"
		phrase = random.choice(phrases)
		# whether the user set a custom user_one
		custom_u1 = (user_one if isinstance(user_one, str) else user_one.id) != ctx.author.id

		pingable: list[Snowflake_Type] = []
		if isinstance(user_one, User):
			if not custom_u1:
				pingable.append(user_one.id)
			user_one = f"<@{user_one.id}>"
		if isinstance(user_two, User):
			if not custom_u1:
				pingable.append(user_two.id)
			user_two = f"<@{user_two.id}>"
		allowed_mentions = AllowedMentions(parse=[], users=list(set(pingable)))
		ctxmsg = ctx.message
		assert ctxmsg is not None
		try:
			try:
				msg = await ctx.channel.send(content=phrase, allowed_mentions=allowed_mentions)
			except:
				msg = await ctx.respond(content=phrase, ephemeral=False, allowed_mentions=allowed_mentions)
		except Exception as e:
			await ctxmsg.edit(content="[ Failed to send the interaction ]")
			raise e
		if user_two.lower() in [
		    ctx.client.user.mention, "twm", "the world machine", "world machine", "theworldmachine", "worldmachine"
		]:
			await asyncio.sleep(random.choice([ 2, 1.5, 0.5, 0 ]))
			await msg.add_reaction("1023573456664662066")
