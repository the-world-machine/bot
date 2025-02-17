import asyncio
from datetime import datetime
import re
from typing import Literal
from interactions import *
from utilities.config import debugging, get_config
from utilities.emojis import emojis
from utilities.mediagen.textbox import Frame, Styles, render_textbox
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message
from utilities.misc import make_empty_select, pretty_user
from utilities.textbox.characters import Character, Face, get_character, get_character_list, get_characters


class State:
	owner: int
	frames: dict[int, Frame]
	filetype: Literal["webp", "gif", "apng", "png", "gif"]
	def ready(self):
		return all(frame.check() for frame in self.frames.values())

	def __init__(self, owner: int, filetype: Literal["webp", "gif", "apng", "png", "gif"] = "webp", frames: dict[int, Frame] | list[Frame] | Frame | None = None):
		self.owner = owner
		self.filetype = filetype
		self.frames = {}
		if not frames:
			return
		if isinstance(frames, Frame):
			self.frames[int(0)] = frames
			return
		for i in range(0, len(frames)):
			self.frames[int(i)] = Frame(frames[i])

	def __repr__(self):
		return f"State(owner={self.owner}, len(frames)={len(self.frames)})"


states = {}


class TextboxCommands(Extension):

	@staticmethod
	def make_characters_select_menu(
	    loc: Localization = Localization(), default: str = None, custom_id: str = "textbox update_char -1"
	):
		characters = get_characters()

		select = StringSelectMenu(placeholder=loc.l("textbox.select.chars"), custom_id=custom_id)
		dedup = False
		for (id, char) in characters:
			option = StringSelectOption(
			    label=id, value=id
			)  # TODO: Localization(in=LocPaths.Textboxes, "{id}.localized")
			option.emoji = char.get_icon_emoji()

			if not dedup and default == id:
				#    ^^^^^ If you pass more than 1 option with default = True discord will exlpode
				option.default = True

			select.options.append(option)

		return select

	@staticmethod
	def make_faces_select_menu(
	    loc: Localization = Localization(),
	    character_id: str = None,
	    custom_id: str = "textbox update_face 0 -1",
	    default: str = None
	):
		try:
			character = get_character(character_id)
		except Exception:
			return make_empty_select(loc=loc, placeholder=loc.l("textbox.errors.no_char"))

		select = StringSelectMenu(custom_id=custom_id, placeholder=loc.l("textbox.select.faces"))

		dedup = False
		for name, face in character.get_faces():
			option = StringSelectOption(
			    label=name, value=name
			)  # TODO: label=Localization(in=LocPaths.Textboxes, "{id}.faces.{name}")
			option.emoji = face.get_icon_emoji()
			if not dedup and default == name:
				option.default = True
			if len(select.options) > 24:
				return select
			select.options.append(option)

		return select

	@slash_command(description="Methods related to Textboxes")
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def textbox(self, ctx: SlashContext):
		pass

	@textbox.subcommand(sub_cmd_description='Make a OneShot textbox')
	@slash_option(
			name='text',
			description='What you want the character to say?',
			opt_type=OptionType.STRING,
			required=False,
			max_length=get_config("textbox.max-text-length-per-frame")
	)
	@slash_option(
	    name='character',
	    description='Which character do you want to be shown on the textbox',
	    opt_type=OptionType.STRING,
	    required=False
	)  # TODO: autocomplete
	@slash_option(
	    name='face',
	    description="Which face of the character do you want?",
	    opt_type=OptionType.STRING,
	    required=False
	)  # TODO: autocomplete
	@slash_option(
	    name='animated',
	    description='Do you want the textbox to animate? (will take longer to render, will be a GIF)',
	    opt_type=OptionType.BOOLEAN,
	    required=False
	)
	@slash_option(
	    name='send',
	    description=
	    'Do you want the image to be sent in this channel right away?', # TODO: use render&send button instead
	    opt_type=OptionType.BOOLEAN,
	    required=False
	)
	async def create(
	    self,
	    ctx: SlashContext,
	    text: str = None,
	    character: str = None,
	    face: str = None,
	    animated: bool = True,
	    send: bool = False
	):
		await fancy_message(ctx, Localization(ctx.locale).l("general.loading"), ephemeral=True)
		state_id = str(ctx.id)  # state_id is the initial `/textbox create` interaction's id
		loc = Localization(ctx.locale)
		"""@slash_option(
				description='Do you want the image to be sent in the channel right away? (given that all of the arguments are properly filled in)', # TODO: add a better way to send in the channel without this option
				name='autosend',
				opt_type=OptionType.BOOLEAN
		)
		@slash_option(
			description='Which filetype do you want the output to be in?',
			name="filetype",
			opt_type=OptionType.STRING,
			choices=[SlashCommandChoice(name="WEBP", value="webp"), SlashCommandChoice(name="GIF", value="gif"), SlashCommandChoice(name="APNG", value="apng"), SlashCommandChoice(name="PNG", value="png"), SlashCommandChoice(name="JPG", value="jpg")]
		)
		"""
		if character:
			try:
				char = get_character(character)
			except ValueError as e:
				return await fancy_message(
						ctx, loc.l("textbox.errors.invalid_character", character_name=character), color=Colors.BAD, edit=True
				)
		if face and char:
			try:
				char.get_face(face)
			except ValueError as e:
				return await fancy_message(
						ctx, loc.l("textbox.errors.invalid_face", face_name=face, character_name=character), color=Colors.BAD, edit=True
				)

		states[state_id] = state = State(
		    owner=ctx.user.id,
				filetype="gif",
				frames=Frame(text=text, animated=animated, character_id=character, face_name=face)
		)

		if send and state.ready():
			await ctx.edit(embed=Embed(description=loc.l("textbox.monologue.rendering"), color=Colors.DARKER_WHITE))
			start=datetime.now()
			file = await self.make_frame(ctx, state.frames[0])
			end=datetime.now()
			took=start-end
			asyncio.create_task(
			    ctx.edit(embed=Embed(description=loc.l("textbox.monologue.uploading"), color=Colors.DARKER_WHITE))
			)
			if ctx.guild_id:
				await ctx.channel.send(
				    content=f"-# [ {ctx.user.mention} ]", files=file, allowed_mentions={ 'users': []}
				)
			else:
				await ctx.send(content=f"-# [ {ctx.user.mention} ]", files=file, allowed_mentions={ 'users': []})
			desc = loc.l("textbox.monologue.done")
			if debugging():
				desc+=loc.l("textbox.monologue.debug", took=took.total_seconds, sid=state_id)
			return await ctx.edit(embed=Embed(description=desc, color=Colors.DEFAULT))

		await self.respond(ctx, state_id, 0)

	@staticmethod
	async def get_basic(loc, ctx, state_id: str, frame_index: str):
		try:
			state: State = states[state_id]
		except KeyError as e:
			await fancy_message(
			    ctx, loc.l("textbox.errors.unknown_state", discord_invite="https://discord.gg/SXzqfhBtkk")
			)  # TODO: move discord invite to bot config
			raise e
		try:
			frame_data: Frame = state.frames[int(frame_index)]
		except IndexError as e:
			await fancy_message(
			    ctx, loc.l("textbox.errors.unknown_frame", index=int(frame_index) + 1, total=len(state.frames))
			)
			raise e
		return (state, frame_data)

	handle_components_regex = re.compile(
	    r"textbox (?P<method>render|update_(char|face|style|text|animated)) (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$"
	)

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		loc = Localization(ctx.locale)
		match = self.handle_components_regex.match(ctx.custom_id)
		if len(match.groups()) <= 3:
			return ctx.edit_origin()
		method, state_id, frame_index = match.group("method", "state_id", "frame_index")
		state, frame_data = await self.get_basic(loc, ctx, state_id, frame_index)

		match method:
			case "update_char":
				frame_data.character_id = ctx.values[0]
				frame_data.face_name = None
			case "update_face":
				frame_data.face_name = ctx.values[0]
			case "update_style":
				frame_data.style = ctx.values[0]
			case "update_text":
				return await self.init_update_text_flow(ctx, state_id, frame_index)
			case "update_animated":
				frame_data.animated = not frame_data.animated
			case "render":
				await ctx.edit_origin(
				    embed=Embed(description=loc.l("textbox.monologue.rendering"), color=Colors.DARKER_WHITE)
				)
				file = await self.make_frame(ctx, state.frames[int(frame_index)])
				asyncio.create_task(
				    ctx.edit(embed=Embed(description=loc.l("textbox.monologue.uploading"), color=Colors.DARKER_WHITE))
				)
				await ctx.edit(files=file)

				return await ctx.edit(embed=Embed(description=loc.l("textbox.monologue.done"), color=Colors.DEFAULT))

		await self.respond(ctx, state_id, frame_index)

	async def make_frame(self, ctx: ComponentContext|SlashContext, frame: Frame, preview: bool = False):
		loc = Localization(ctx.locale)
		char = get_character(frame.character_id)
		face = char.get_face(frame.face_name)

		if frame.face_name == 'Your Avatar':
			await face.set_custom_icon(ctx.author.avatar.url)

		filename = loc.l("textbox.single.name", character=frame.character_id, face=frame.face_name,timestamp=datetime.now().timestamp())
		alt_text = \
		loc.l(f"textbox.single.alt.{ \
			"avatar" if frame.face_name == "Your Avatar" \
			else "other" if frame.character_id == "Other" \
			else "character" \
			}.{ \
				"left" if frame.style == Styles.NORMAL_LEFT else "right" \
			}",
				character=frame.character_id, 
				face=frame.face_name, 
				username=pretty_user(ctx.author), 
				name=frame.face_name
		)# yapf: ignore
			
		text = frame.text
		alt_text = loc.l(f'textbox.single.alt.{"cont" if text else "cont_silly"}', text=text, alt=alt_text)  
		if not text:
			text = loc.l("textbox.placeholder_text")
		return await render_textbox(text, face, not preview if preview else frame.animated, filename, alt_text)

	async def respond(self, ctx: SlashContext | ComponentContext | ModalContext, state_id: str, frame_index: int):
		loc = Localization(ctx.locale)
		state, frame_data = await self.get_basic(loc, ctx, state_id, frame_index)

		files = []
		if state.frames[int(frame_index)].check():
			files.append(await self.make_frame(ctx, state.frames[int(frame_index)], preview=True))
		embed = Embed(
		    color=Colors.DEFAULT,
		    description=loc.l("textbox.monologue.char")
		    if frame_data.character_id is None else loc.l("textbox.monologue.face") if frame_data.face_name is None else
		    loc.l("textbox.monologue.press") if frame_data.text else loc.l("textbox.monologue.press_notext")
		)
		components = [
		    ActionRow(
		        self.make_characters_select_menu(
		            loc, custom_id=f"textbox update_char {state_id} {frame_index}", default=frame_data.character_id
		        )
		    ),
		    ActionRow(
		        make_empty_select(loc, placeholder=loc.l("textbox.select.faces"))
		        if frame_data.face_name is None and frame_data.character_id is None else self.make_faces_select_menu(
		            loc,
		            custom_id=f"textbox update_face {state_id} {frame_index}",
		            character_id=frame_data.character_id,
		            default=frame_data.face_name
		        )
		    ),
		    ActionRow(
		        Button(
		            style=ButtonStyle.GRAY,
		            label=loc.l("textbox.button.text"),
		            custom_id=f"textbox update_text {state_id} {frame_index}",
		            disabled=not state
		        ),
		        Button(
		            style=ButtonStyle.GREEN,
		            label=loc.l("textbox.button.render", type=loc.l(f"textbox.filetypes.{state.filetype}")),
		            custom_id=f"textbox render {state_id} 0",
		            disabled=not state.ready()
		        )
		    )
		]

		if isinstance(ctx, ComponentContext):
			return await ctx.edit_origin(embed=embed, components=components, files=files)
		else:
			return await ctx.edit(
			    message=ctx.message_id if isinstance(ctx, ModalContext) else "@original",
			    embed=embed,
			    components=components,
			    files=files
			)

	async def init_update_text_flow(self, ctx: ComponentContext | SlashContext, state_id: str, frame_index: str):
		loc = Localization(ctx.locale)
		state, frame_data = await self.get_basic(loc, ctx, state_id, frame_index)
		modal = Modal(
		    ShortText(
		        custom_id='new_text',
		        value=frame_data.text,
		        label=loc.l('textbox.modal.edit_text.input.label', index=int(frame_index) + 1),
		        placeholder=loc.l('textbox.modal.edit_text.input.placeholder'),
		        max_length=get_config("textbox.max-text-length-per-frame")
		    ),
		    custom_id=f'textbox update_text_finish {state_id} {frame_index}',
		    title=loc.l('textbox.modal.edit_text.title', index=int(frame_index) + 1, total=len(state.frames))
		)
		await ctx.send_modal(modal)

	handle_modal_regex = re.compile(r"textbox update_text_finish (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$")

	@modal_callback(handle_modal_regex)
	async def handle_modals(self, ctx: ModalContext, new_text: str):
		loc = Localization(ctx.locale)

		match = self.handle_modal_regex.match(ctx.custom_id)
		if len(match.groups()) < 2:
			return ctx.edit_origin()
		state_id, frame_index = match.group("state_id", "frame_index")
		state, frame_data = await self.get_basic(loc, ctx, state_id, frame_index)
		old_text = frame_data.text
		frame_data.text = new_text
		if debugging():
			await fancy_message(
					ctx, loc.l('textbox.modal.edit_text.response', new_text=new_text, old_text=old_text), ephemeral=True
			)
		await self.respond(ctx, state_id, frame_index)
