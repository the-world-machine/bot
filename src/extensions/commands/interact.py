from __future__ import annotations
import asyncio
from dataclasses import dataclass
import random
import re
from typing import Any
from interactions import ActionRow, Button, ButtonStyle, ComponentContext, ContextMenuContext, Embed, Extension, Member, MentionType, Message, OptionType, PartialEmoji, SlashContext, Snowflake_Type, User, component_callback, contexts, integration_types, message_context_menu, slash_command, slash_option, user_context_menu, AllowedMentions
from utilities.config import debugging
from utilities.emojis import emojis
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message

invis_char = "󠄴"

none_allowed = AllowedMentions(parse=[], roles=[], users=[])


class InteractionEntry:
	name: str | None
	phrases: list[InteractionEntry | str]

	def __init__(
	    self, name: str | None, phrases: list[InteractionEntry | dict | str] | tuple[InteractionEntry | dict | str]
	):
		self.name = name
		self.phrases = []
		for entry in phrases:
			if not isinstance(entry, InteractionEntry):
				if not isinstance(entry, (str, dict)):
					raise ValueError(f"Entry '{entry}' is not a string or a dict")
				if isinstance(entry, dict):
					entry = InteractionEntry(entry['name'], entry['phrases'])
			self.phrases.append(entry)


def fill_with_none(arr, target_index):
	current_length = len(arr)
	if target_index >= current_length:
		arr += [None] * (target_index - current_length + 1)
	return arr


def replace_numbers_with_emojis(text: str) -> str:
	return re.sub(r'\d', lambda m: m.group() + chr(0xFE0F) + chr(0x20E3), text)


# Example usage
text = "I have 3 apples and 15 oranges, but only 0.5 bananas."
emoji_text = replace_numbers_with_emojis(text)
print(emoji_text)


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

	@staticmethod
	def ie_only_basic(phrases: list[InteractionEntry | str]):
		return all(isinstance(phrase, str) for phrase in phrases)

	@staticmethod
	def format_mention(user: str | User | None):
		global invis_char
		if isinstance(user, str):
			user = user.replace("``", f"`{invis_char}`")
			if (user.startswith("<") and user.endswith(">")) or user in [ "@everyone", "@here", "@someone"]:
				return user
			return ("``" + user + "``")
		elif isinstance(user, User):
			return f'<@{user.id}>'
		else:
			return "someone"

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
		await ctx.respond(content=loc.l('general.loading'), ephemeral=False)
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
		return await self.respond((ctx, loc), (0, ".phrases", user_one, user_two))

	handle_components_regex = re.compile(r"interact (?P<page>.+) (?P<path>.+)$")

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		loc = Localization(ctx.locale)
		assert ctx.message is not None, "discorded"
		content = ctx.message.content
		content = content.replace("→ :i: →", "→ ❔ →")
		content = content.replace(f"→ {emojis['icons']['loading']} →", "→ ❔ →")
		stuff = content.partition("→ ❔ →")
		await ctx.edit_origin(
		    content=stuff[0] + stuff[1].replace("❔", emojis['icons']['loading']) + stuff[2],
		    allowed_mentions=none_allowed
		)
		match = self.handle_components_regex.match(ctx.custom_id)
		if match:
			page, path = match.group("page", "path")
		assert isinstance(page, str) and isinstance(path, str)

		user_one = stuff[0][2:-1]
		user_two = stuff[2][1:-2]
		if user_one.startswith("``"):
			user_one = user_one[2:-2]
		if user_two.startswith("``"):
			user_two = user_two[2:-2]
		user_one, user_two = await self.parse_args(ctx, user_one, user_two)
		try:
			interaction_raw = loc.l(f"interact{path}", typecheck=Any)
			assert not isinstance(interaction_raw, str)
			interaction = InteractionEntry(interaction_raw['name'], phrases=interaction_raw['phrases']) if isinstance(
			    interaction_raw, dict
			) else InteractionEntry(None, interaction_raw)
		except BaseException as e:
			print(e)
			return await ctx.send(
			    embeds=Embed(
			        description=f"[ {loc.l('interact.errors.no_path')} ]" +
			        ("" if not debugging() else f"\n-# Debug: {e}"),
			        color=Colors.BAD
			    )
			)
		if not isinstance(interaction, tuple) and self.ie_only_basic(interaction.phrases):
			await self.send_phrase((ctx, loc), (path, user_one, user_two))
			return await ctx.message.edit(content=''.join(stuff), allowed_mentions=none_allowed)
		return await self.respond((ctx, loc), (int(page), path, user_one, user_two))

	async def respond(
	    self, cx: tuple[ComponentContext | ContextMenuContext | SlashContext, Localization],
	    state: tuple[int, str, str | User, str | User]
	):
		ctx, loc = cx
		page, path, user_one, user_two = state
		interaction_raw: dict | tuple = loc.l(f"interact{path}", typecheck=Any)  # type:ignore
		assert not isinstance(interaction_raw, str)
		interaction = InteractionEntry(interaction_raw['name'], phrases=interaction_raw['phrases']) if isinstance(
		    interaction_raw, dict
		) else InteractionEntry(None, interaction_raw)
		phrases = interaction.phrases
		all_buttons: list[Button] = []
		for i in range(len(phrases)):
			phrase = phrases[i]
			if isinstance(phrase, str):
				return await ctx.send(embeds=Embed(description=f"[ {loc.l('interact.errors.500')} ]", color=Colors.BAD))

			button = Button(style=ButtonStyle.GRAY, label=phrase.name, custom_id=f"interact {page} {path}[{i}]")
			if not self.ie_only_basic(phrase.phrases):
				button.style = ButtonStyle.BLURPLE
				button.emoji = PartialEmoji(name="🔢")
			else:
				if interaction.name is not None:
					button.custom_id = f"interact {page} {path}.phrases[{i}]"
			all_buttons.append(button)

		all_buttons = sorted(
		    all_buttons,
		    key=lambda button: ((button.emoji.name != "🔢" if button.emoji is not None else True), button.label)
		)
		buttons: list[Button | None] = []
		buttons_per_page = 25

		if interaction.name is not None:
			out = path.rpartition('[')
			buttons_per_page -= 2
			buttons.append(
			    Button(
			        label=interaction.name,
			        style=ButtonStyle.BLURPLE,
			        disabled=True,
			        emoji=PartialEmoji(name="🔢"),
			        custom_id=f"unused",
			    )
			)
			buttons.append(
			    Button(
			        style=ButtonStyle.BLURPLE,
			        disabled=False,
			        emoji=PartialEmoji(name="⬆️"),
			        custom_id=f"interact {page} {out[0]}",
			    )
			)
		paging = len(all_buttons) > buttons_per_page
		if paging:
			buttons_per_page -= 1
			buttons.insert(
			    0,
			    Button(
			        label=replace_numbers_with_emojis(str(page)),
			        style=ButtonStyle.GRAY,
			        disabled=True,
			        emoji=PartialEmoji(name="🔢"),
			        custom_id=f"unused",
			    )
			)
			buttons_per_page -= 1  # next button
			if page > 0 and page < len(all_buttons) / buttons_per_page:
				buttons_per_page -= 1  # prev button
		buttons.extend(all_buttons[page:page + 1 + buttons_per_page])
		if paging and page != 0:
			buttons = fill_with_none(buttons, 5)
			buttons.insert(0, Button(custom_id=f"interact {page-1} {path}", style=ButtonStyle.BLURPLE, emoji="⬅️"))
		if paging and page < len(all_buttons) / buttons_per_page:
			buttons.insert(4, Button(custom_id=f"interact {page+1} {path}", style=ButtonStyle.BLURPLE, emoji="➡️"))

		rows = [ActionRow(*[ btn for btn in buttons[i:i + 5] if btn is not None ]) for i in range(0, len(buttons), 5)]
		return await ctx.edit(
		    content=f"[ {self.format_mention(user_one)} → ❔ → {self.format_mention(user_two)} ]",
		    embeds=[],
		    components=rows,
		    allowed_mentions=none_allowed
		)

	async def send_phrase(
	    self, cx: tuple[ComponentContext | ContextMenuContext | SlashContext, Localization],
	    state: tuple[str, str | User, str | User]
	):
		ctx, loc = cx
		quote_path, user_one, user_two = state

		interaction: Any = loc.l(
		    f"interact{quote_path}",
		    typecheck=Any,
		    user_one=self.format_mention(user_one),
		    user_two=self.format_mention(user_two)
		)
		phrase = random.choice(interaction['phrases'])
		# whether the user set a custom user_one
		custom_u1 = (user_one if isinstance(user_one, str) else user_one.id) != ctx.author.id

		pingable: list[Snowflake_Type] = []
		if isinstance(user_one, User) and not custom_u1:
			pingable.append(user_one.id)
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
			return await ctx.send(embeds=Embed(description=f"[ {loc.l('interact.errors.fail')} ]", color=Colors.BAD))
			raise e
		if user_two.lower() in [
		    f"<@{ctx.client.user.id}>", "@twm", "@the world machine", "@world machine", "@theworldmachine",
		    "@worldmachine"
		]:
			await asyncio.sleep(random.choice([ 2, 1.5, 0.5, 0 ]))
			await msg.add_reaction("1023573456664662066")
