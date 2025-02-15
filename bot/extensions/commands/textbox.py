import asyncio
import os
import re
from typing import Callable, Literal, Optional
import yaml
from interactions import *
from utilities.emojis import emojis
from utilities.media import generate_dialogue
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message
from utilities.misc import make_empty_select


class Face:
	name: str
	emoji: str

	def __init__(self, name: str, emoji: int):
		self.name = str(name)
		self.emoji = str(emoji)

	def __repr__(self):
		return f"Face(name={self.name}, emoji={self.emoji})"


class Character:
	id: str
	faces: list[Face]

	def __init__(self, id: str, faces: list[Face]):
		self.id = id
		self.faces = faces

	def __repr__(self):
		return f"Character(id={self.name}, faces={self.faces})"


class Frame:
	type: Literal[0, 1] = 0
	text: str | None
	character: Character | None
	face: Face | None
	speed: float = 1.00

	def check(self):
		return self.text is not None and self.character is not None and self.face is not None

	def __init__(
	    self,
	    type: Literal[0, 1] = 0,
	    text: str | None = None,
	    character: str | None = None,
	    face: str | None = None,
	    speed: float = 1.00
	):
		self.type = type
		self.text = text
		self.character = character
		self.face = face
		if speed < 0.01:
			raise ValueError("Speed must be above 0.01")
		self.speed = speed

	def __repr__(self):
		return f"Frame(character={self.character}, face={self.face}, speed={self.speed})"


class State:
	global Frame
	owner: int
	animated: bool
	frames: dict[int, Frame]

	def ready(self):
		return all(frame.check() for frame in self.frames.values())

	def __init__(
	    self, owner: int, animated: bool = False, frames: dict[int, Frame] | list[Frame] | Frame | None = None
	):
		self.owner = owner
		self.animated = animated
		self.frames = {}
		if not frames:
			return
		if isinstance(frames, Frame):
			self.frames[0] = frames
			return
		for i in range(0, len(frames)):
			self.frames[i] = Frame(frames[i])

	def __repr__(self):
		return f"State(owner={self.owner}, animated={self.animated}, len(frames)={len(self.frames)})"


states = {}
"""State(
	owner=message.author.id,
	animated=True,
	frames=Frame(
		text="HellO wO or Hell OwO",
		character="Ling",
		face=None
	)
))"""


class TextboxCommands(Extension):
	_characters = None
	_last_modified = None

	@staticmethod
	def get_characters() -> list[Character]:
		path = 'bot/data/characters.yml'
		# TODO: use watcher instead
		if TextboxCommands._characters is None or (os.path.getmtime(path) != TextboxCommands._last_modified):
			with open(path, 'r') as f:
				data = yaml.safe_load(f)
				TextboxCommands._characters = [
				    Character(
				        id=character['id'],
				        faces=[Face(name=face['name'], emoji=str(face['emoji'])) for face in character['faces']]
				    ) for character in data['characters']
				]
				TextboxCommands._last_modified = os.path.getmtime(path)

		return TextboxCommands._characters

	@staticmethod
	def get_character(id: str, characters: list[Character] | None = None) -> Character:
		if characters is None:
			characters = TextboxCommands.get_characters(
			)  # i wonder how to replace this so   i don't have to copypaste everywher
		for char in characters:
			if char.id == id:
				return char

	@staticmethod
	def make_characters_select_menu(
	    loc: Localization = Localization(),
	    default: str = None,
	    custom_id: str = "textbox update_char -1",
	    characters: list[Character] = None
	):
		if characters is None:
			characters = TextboxCommands.get_characters()

		select = StringSelectMenu(placeholder=loc.l("textbox.select.chars"), custom_id=custom_id)
		dedup = False
		for character in characters:
			option = StringSelectOption(label=character.id, value=character.id)  # TODO: change .id to localized name
			option.emoji = PartialEmoji(id=str(character.faces[0].emoji))

			if not dedup and default == character.id:
				#    ^^^^^ If you pass more than 1 option with default = True discord will exlpode
				option.default = True

			select.options.append(option)

		return select

	@staticmethod
	def make_faces_select_menu(
	    loc: Localization = Localization(),
	    character_id: str = None,
	    custom_id: str = "textbox update_face 0 -1",
	    default: str = None,
	    characters: list[Character] = None
	):
		if characters is None:
			characters = TextboxCommands.get_characters()

		character = next((char for char in characters if char.id == character_id), None)
		if character is None:
			raise ValueError(f"Character '{character_id}' not found.")

		select = StringSelectMenu(custom_id=custom_id, placeholder=loc.l("textbox.select.faces"))

		dedup = False
		for face in character.faces:
			option = StringSelectOption(label=face.name, value=face.emoji)
			option.emoji = PartialEmoji(id=str(face.emoji))
			if not dedup and default == face.emoji:
				#    ^^^^^ If you pass more than 1 option with default = True discord will exlpode
				option.default = True

			select.options.append(option)

		return select

	@slash_command(description="Methods related to Textboxes")
	@integration_types(guild=True, user=False)
	@contexts(bot_dm=False)
	async def textbox(self, ctx: SlashContext):
		pass

	@textbox.subcommand(sub_cmd_description='Make a OneShot textbox')
	@slash_option(
	    description='What you want the character to say?', name='text', opt_type=OptionType.STRING, required=False
	)
	@slash_option(
	    description='The character you want to be shown on the textbox',
	    name='character',
	    opt_type=OptionType.STRING,
	    required=False
	)  # TODO: autocomplete
	@slash_option(
	    description="Which face of the character do you want? (don't specify this if you want to preview them)",
	    name='face',
	    opt_type=OptionType.STRING,
	    required=False
	)  # TODO: autocomplete
	@slash_option(
	    description='Do you want the text to appear slowly? (will take longer to generate)',
	    name='animated',
	    opt_type=OptionType.BOOLEAN
	)
	async def create(
	    self, ctx: SlashContext, text: str = None, character: str = None, face: str = None, animated: bool = False
	):
		await fancy_message(ctx, Localization(ctx.locale).l("general.loading"), ephemeral=True)
		sid = str(ctx.id)  # state_id is the initial `/textbox create` interaction's id
		states[sid] = State(
		    owner=ctx.user.id, animated=animated, frames=Frame(text=text, character=character, face=face)
		)
		await self.respond(ctx, sid, 0)

	char_select_regex = re.compile(r"textbox update_char (\d+) (\d+)$")

	@component_callback(char_select_regex)
	async def char_select(self, ctx: ComponentContext):
		match = self.char_select_regex.match(ctx.custom_id)
		if len(match.groups()) <= 0:
			return ctx.edit_origin()
		frame = match.group(2)  # state_id is the interaction id
		sid = match.group(1)  # state_id is the interaction id
		try:
			state: State = states[sid]
		except KeyError as e:  # TODO: the states object gets reset every time the bot restarts, need a warning about this to the user
			return await ctx.send("state not found")

		try:
			frame_data: Frame = state.frames[int(frame)]
		except IndexError as e:
			return await ctx.send(f'frame "{frame}" not found. there are {len(state.frames)}')
		frame_data.character = ctx.values[0]
		frame_data.face = None

		await self.respond(ctx, sid, frame)

	face_select_regex = re.compile(r"textbox update_face (\d+) (\d+)$")

	@component_callback(face_select_regex)
	async def face_select(self, ctx: ComponentContext):
		match = self.face_select_regex.match(ctx.custom_id)
		if len(match.groups()) <= 0:
			return ctx.edit_origin()
		frame = match.group(2)
		sid = match.group(1)
		try:
			state: State = states[sid]
		except KeyError as e:
			return await ctx.send("state not found")

		try:
			frame_data: Frame = state.frames[int(frame)]
		except IndexError as e:
			return await ctx.send(f'frame "{frame}" not found. there are {len(state.frames)}')

		frame_data.face = ctx.values[0]
		await self.respond(ctx, sid, frame)

	generate_button_regex = re.compile(r"textbox generate (\d+)$")

	@component_callback(generate_button_regex)
	async def generate_button(self, ctx: ComponentContext):
		loc = Localization(ctx.locale)
		await ctx.defer(edit_origin=True)
		match = self.generate_button_regex.match(ctx.custom_id)
		if len(match.groups()) <= 0:
			return ctx.edit_origin()
		sid = match.group(1)
		try:
			state: State = states[sid]
		except KeyError as e:
			return await ctx.send("state not found")

		await ctx.edit(embed=Embed(description=loc.l("textbox.monologue.generating"), color=Colors.DARKER_WHITE))
		file = await self.make_frame(ctx, state.frames[0], animated=state.animated)
		asyncio.create_task(
		    ctx.edit(embed=Embed(description=loc.l("textbox.monologue.uploading"), color=Colors.DARKER_WHITE))
		)

		await ctx.edit(files=file)

		await ctx.edit(embed=Embed(description=loc.l("textbox.monologue.done"), color=Colors.DEFAULT))

	async def make_frame(self, ctx, frame: Frame, animated, filename: str = None, alt_text: str = None):
		if frame.face == '964952736460312576':
			icon = ctx.author.avatar.url
		else:
			icon = f'https://cdn.discordapp.com/emojis/{frame.face}.png'
		return await generate_dialogue(frame.text, icon, animated, filename, alt_text)

	async def respond(self, ctx: SlashContext | ComponentContext, sid: str, frame: int):
		loc = Localization(ctx.locale)
		try:
			state: State = states[sid]
		except KeyError as e:  # TODO: the states object gets reset every time the bot restarts, need a warning about this to the user
			return await ctx.send("state not found")
		try:
			frame_data: Frame = state.frames[int(frame)]
		except IndexError as e:
			return await ctx.send(f'frame "{frame}" not found. there are {len(state.frames)}')
		"""states[sid] = State(
			owner=ctx.user.id,
			animated=animated,
		  frames=Frame(text=text, character=character, face=face)
		)"""
		return await (ctx.edit_origin if isinstance(ctx, ComponentContext) else ctx.edit)(
		    embed=Embed(
		        color=Colors.DEFAULT,
		        description=loc.l("textbox.monologue.char") if frame_data.character is None else
		        loc.l("textbox.monologue.face") if frame_data.face is None else loc.l("textbox.monologue.press")
		    ),
		    components=[
		        ActionRow(
		            self.make_characters_select_menu(
		                loc, custom_id=f"textbox update_char {sid} 0", default=frame_data.character
		            )
		        ),
		        ActionRow(
		            make_empty_select(loc, placeholder=loc.l("textbox.select.faces"))
		            if frame_data.face is None and frame_data.character is None else self.make_faces_select_menu(
		                loc,
		                custom_id=f"textbox update_face {sid} 0",
		                character_id=frame_data.character,
		                default=frame_data.face
		            )
		        ),
		        ActionRow(
		            Button(
		                style=ButtonStyle.GREEN,
		                label=loc.l("textbox.button.generate"),
		                custom_id=f"textbox generate {sid}",
		                disabled=not state.ready()
		            )
		        )
		    ]
		)
