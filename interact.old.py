# type:ignore
from __future__ import annotations
import re
import random
import asyncio
from dataclasses import dataclass
from utilities.message_decorations import *
from utilities.localization import Localization, assign_variables
from interactions import *

@dataclass(frozen=True)
class InteractionEntry:
	name: str
	messages: tuple[InteractionEntry | str]




	handle_components_regex = re.compile(r"interact (?P<user_two>.+) (?P<path>.+)$")

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		await fancy_message(ctx, Localization(ctx.locale).l('general.loading'), ephemeral=True, edit_origin=True)
		match = self.handle_components_regex.match(ctx.custom_id)
		if match:
			user_two, path = match.group("user_two", "path")
			return await self.respond(ctx, path, user_two)

	@staticmethod
	def fat_condition(messages):
		return (isinstance(messages, tuple) and all(isinstance(msg, dict) for msg in messages) and len(messages) > 1)

	async def main(self, ctx: ContextMenuContext | ComponentContext | SlashContext, user_two: str):
		loc = Localization(ctx.locale)
		messages: tuple[InteractionEntry] | str | InteractionEntry = loc.l(f'interact.options{path.split("main")[1]}', typecheck=Any)
		# if it failed to find the localization string somehow, may also be an old button that got triggered somehow
		if isinstance(messages, str):
			if messages.startswith("`"): 
				return await ctx.edit()
		
		if isinstance(messages, tuple) and len(messages) == 1 and isinstance(messages[0], InteractionEntry) and all(
		    isinstance(msg, str) for msg in messages[0]['messages']
		):
			messages = messages[0]
		else:
			
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

	async def send_phrase(self, ctx, quote: str, user_one: str, user_two: str):
		...

	async def respond(self, ctx, state: str = ""):
		if str == "":
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