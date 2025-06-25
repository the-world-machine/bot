import asyncio
from datetime import datetime
import io
import re
from typing import Literal
from interactions import *
from utilities.config import debugging, get_config
from utilities.emojis import emojis
from utilities.mediagen.textboxes import Frame, BackgroundStyle, render_textbox, render_textbox_frames
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message
from utilities.misc import make_empty_select, optionSearch, pretty_user
from utilities.textbox.characters import Character, Face, get_character, get_character_list, get_characters

states = {}
SupportedFiletypes = Literal["WEBP", "GIF", "APNG", "PNG", "JPEG"]
class StateOptions:
	out_filetype: SupportedFiletypes # TODO: m,ake this use an enum
	send_to: 1 | 2 | 3 # TODO: m,ake this use an enum
	quality: int 

	def __init__(self, filetype: SupportedFiletypes = "WEBP", send_to: 1 | 2 | 3 = 1, quality: int = 100):
		self.out_filetype = filetype
		self.send_to = send_to
		self.quality = quality


	def __repr__(self):
		attrs = {k: getattr(self, k) for k in self.__annotations__}
		attrs_str = ", ".join(f"{k}={repr(v)}" for k, v in attrs.items())
		return f"StateOptions({attrs_str})"

class State:
	owner: int
	frames: dict[int, Frame]
	options: StateOptions

	def __init__(self, owner: int, frames: dict[int, Frame] | list[Frame] | Frame = None, options: StateOptions = None):
		self.options = options if options else StateOptions()
		self.owner = owner
		self.frames = {}
		if not frames:
			return
		if isinstance(frames, Frame):
			self.frames[int(0)] = frames
			return
		for i in range(0, len(frames)):
			self.frames[int(i)] = Frame(frames[i])

	def __repr__(self):
		return (
			f"State(\n"+
			f"  owner={self.owner},\n"+
			f"  frames: len()={len(self.frames)}; [\n"+
			f"{",\n".join(f"      {repr(frame)}" for index, frame in self.frames.items())}\n"+
			f"  ]\n"+
			f"  {self.options}\n"
			f")"
		)


class TextboxCommands(Extension):
	global states

	@staticmethod
	def make_characters_select_menu(
	    loc: Localization = Localization(), default: str = None, custom_id: str = "textbox update_char 0"
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
	    custom_id: str = "textbox update_face 0 0",
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

	@slash_command(description="Commands related to Textboxes")
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
			max_length=get_config("textbox.max-text-length-per-frame", as_str=False)
	)
	@slash_option(
	    name='character',
			argument_name='character_id',
	    description='Which character do you want to be shown on the textbox? (default: Other)',
	    opt_type=OptionType.STRING,
	    required=False,
	    autocomplete=True,
	)
	@slash_option(
	    name='face',
			argument_name='face_name',
	    description="Which face of the character do you want? (uses default character if it's not specified)",
	    opt_type=OptionType.STRING,
	    required=False,
	    autocomplete=True,
	)
	@slash_option(
	    name='animated',
	    description='Do you want the text to animate in? (will take longer to render, overrides filetype arg)',
	    opt_type=OptionType.BOOLEAN,
	    required=False
	)
	@slash_option(
		description='What filetype do you want the output to be?',
		name="filetype",
		opt_type=OptionType.STRING,
		choices=[
			SlashCommandChoice(name="WEBP (default)", value="WEBP"),
			SlashCommandChoice(name="GIF", value="GIF"), 
			SlashCommandChoice(name="APNG", value="APNG"), 
			SlashCommandChoice(name="PNG", value="PNG"), 
			SlashCommandChoice(name="JPEG", value="JPEG")
		]
	)
	@slash_option(
	    name='send_to',
	    description='Where do you want the output to be sent? (pass all other arguments for it to render&send right away)',
	    opt_type=OptionType.INTEGER,
	    required=False,
			choices=[
				SlashCommandChoice(name="Don't (default)", value=1), 
				SlashCommandChoice(name="DMs", value=2), 
				SlashCommandChoice(name="This channel (here)", value=3)
			]
	)
	async def create(
	    self,
	    ctx: SlashContext,
	    text: str = None,
	    character_id: str = None,
	    face_name: str = None,
	    animated: bool = None,
			filetype: str = None,
	    send_to: 1 | 2 | 3 = 1
	):
		await fancy_message(ctx, Localization(ctx.locale).l("general.loading"), ephemeral=True)
		state_id = str(ctx.id)  # state_id is the initial `/textbox create` interaction's id, need to save these between restarts later somehow
		loc = Localization(ctx.locale)
		erored = False

		if not character_id and face_name:
			character_id = "Other"

		if character_id:
			try:
				char = get_character(character_id)
			except ValueError as e:
				erored = True
				await fancy_message(
						ctx, loc.l("textbox.errors.invalid_character", character_name=character_id), color=Colors.BAD, edit=True
				)
				character_id = None
				face_name = None


		if face_name and char:
			try:
				f = char.get_face(face_name)
			except ValueError as e:
				erored = True
				await fancy_message(
						ctx, loc.l("textbox.errors.invalid_face", face_name=face_name, character_name=character_id), color=Colors.BAD, edit=True
				)
				face_name = None


		if animated != None:
			filetype = 'WEBP' if animated else 'PNG'
		if not filetype:
			filetype = 'WEBP'

		# init state
		states[state_id] = State(
			owner=ctx.user.id,
			options=StateOptions(
				filetype=filetype,
				send_to=send_to
			),
			frames=Frame(text=text, starting_character_id=character_id, starting_face_name=face_name)
		)

		if send_to != 1 and character_id and face_name:
			# if user specified enough params to send the textbox right after the /command...
			ctx.edit_origin = ctx.edit
			await self.send_output(ctx, state_id, 0)

		await self.respond(ctx, state_id, 0, edit=not erored)

	@create.autocomplete("character")
	async def character_autocomplete(self, ctx: AutocompleteContext):
		loc = Localization(ctx.locale)
		characters = get_characters()
		
		return await ctx.send(optionSearch(ctx.input_text, [{"picked_name": name, "value": name} for name, char in characters]))
	
	@create.autocomplete("face")
	async def face_autocomplete(self, ctx: AutocompleteContext):
		loc = Localization(ctx.locale)
		character = get_character(ctx.kwargs["character"] if "character" in ctx.kwargs else "Other")

		return await ctx.send(optionSearch(ctx.input_text, [{"picked_name": name, "value": name} for name in character.get_face_list()]))
	
	async def basic(self, ctx, state_id: str, frame_index: str):
		loc = Localization(ctx.locale)
		try:
			state: State = states[state_id]
		except KeyError as e:
			await fancy_message(
			    ctx, loc.l("textbox.errors.unknown_state", id=state_id, discord_invite="https://discord.gg/SXzqfhBtkk"), ephemeral=True
			)  # TODO: move discord invite to bot config
			return (loc, None, None)
		try:
			frame_data: Frame = state.frames[int(frame_index)]
		except KeyError as e:
			frame_data = Frame(starting_character_id=state.frames[int(frame_index)-1].starting_character_id)
			state.frames[int(frame_index)] = frame_data
		return (loc, state, frame_data)

	handle_components_regex = re.compile(
	    r"textbox (?P<method>refresh|render|update_(char|face|text|animated)) (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$"
	)

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		match = self.handle_components_regex.match(ctx.custom_id)
		if len(match.groups()) <= 3:
			return ctx.edit_origin()
		method, state_id, frame_index = match.group("method", "state_id", "frame_index")
		loc, state, frame_data = await self.basic(ctx, state_id, frame_index)
		if not loc:
			return
		match method:
			case "update_char":
				frame_data.starting_character_id = ctx.values[0]
				frame_data.starting_face_name = None
			case "update_face":
				frame_data.starting_face_name = ctx.values[0]
			case "update_text":
				return await self.init_update_text_flow(ctx, state_id, frame_index)
			case "update_animated":
				frame_data.animated = not frame_data.animated
			case "render":
				await self.send_output(ctx, state_id, frame_index)
				
		await self.respond(ctx, state_id, frame_index)

	async def send_output(self, ctx: ComponentContext | SlashContext, state_id: str, frame_index: int):
		loc, state, frame_data = await self.basic(ctx, state_id, frame_index)
		pos = ""
		if len(state.frames) > 2 or frame_index != 0:
			pos = "\n\n-# "+loc.l("textbox.frame_position", current=int(frame_index)+1, total=len(state.frames))
		await ctx.edit_origin(
				embed=Embed(description=loc.l("textbox.monologue.rendering")+pos, color=Colors.DARKER_WHITE)
		)

		start=datetime.now()
		file = await self.render_to_file(ctx, state)
		end=datetime.now()
		took=start-end

		mention = { 'users': [] }
		content = f"-# [ {ctx.user.mention} ]"
		try:
			if state.options.send_to == 3:
				if ctx.guild:
					await ctx.channel.send(
						content=content, files=file, allowed_mentions=mention
					)
				else:
					await ctx.send(content=content, files=file, allowed_mentions=mention)
			elif state.options.send_to == 2:
				await ctx.author.send(files=file)
			elif state.options.send_to == 1:
				await ctx.send(content=content, files=file, allowed_mentions=mention, ephemeral=True)
		except: # when it fails to send a dm or a followup to an ephemeral message with a non-ephemeral message
			asyncio.create_task(
					ctx.edit(embed=Embed(description=loc.l("textbox.errors.failed_to_send"+("_dm" if state.options.send_to == 3 else "")), color=Colors.DARKER_WHITE))
			)
		asyncio.create_task(
				ctx.edit(embed=Embed(description=loc.l("textbox.monologue.sending")+pos, color=Colors.DARKER_WHITE))
		)
		desc = loc.l("textbox.monologue.done")
		if debugging():
			desc+="\n-# "+loc.l("textbox.monologue.debug", time=took.total_seconds(), sid=state_id)

		await ctx.edit(embed=Embed(description=desc+pos, color=Colors.DEFAULT))

	async def render_to_file(self, ctx: ComponentContext|SlashContext, state: State, frame_preview_index: int = None) -> File:
		# you do alt text here later dont unabstract this
		loc = Localization(ctx.locale)

		if frame_preview_index is not None:
			frame = state.frames[int(frame_preview_index)]
			char = None
			face = None
			if frame.starting_character_id:
				char = get_character(frame.starting_character_id)
			if char and frame.starting_face_name:
				face = char.get_face(frame.starting_face_name)
				if frame.starting_face_name == 'Your Avatar':
					await face.set_custom_icon(ctx.author.avatar.url) # WARN: this could leak? idk

			filename = loc.l("textbox.alt.single_frame.filename", character=frame.starting_character_id, face=frame.starting_face_name,timestamp=str(round(datetime.now().timestamp())))

		else: # NOT render button
			filename = loc.l("textbox.alt.multi_frame.filename", frames=len(state.frames),timestamp=str(round(datetime.now().timestamp())))
			#alt_accum = ""
			for frame in state.frames.values():
				char = None
				face = None
				if frame.starting_character_id:
					char = get_character(frame.starting_character_id)
				if char and frame.starting_face_name:
					face = char.get_face(frame.starting_face_name)
					if frame.starting_face_name == 'Your Avatar':
						await face.set_custom_icon(ctx.author.avatar.url) # WARN: this could leak? idk

			#	alt_accum = loc.l("textbox.multi.alt.frame" +("" if frame.text else "_nothing"), character=frame.character_id, face=frame.face_name, text=frame.text)
			#alt_text = loc.l("textbox.multi.alt.beginning", frames=alt_accum)

		buffer = await render_textbox_frames(state.frames, state.options.quality, state.options.out_filetype if frame_preview_index is None else "PNG")
		_filetype="."+state.options.out_filetype
		if frame_preview_index is not None:
			_filetype = ".PNG"
		if state.options.out_filetype == "APNG":
			_filetype = ""
		filename = filename + _filetype
		buffer.seek(0)
		return File(file=buffer, file_name=filename)#, description=alt_text if alt_text else frame.text)

	async def init_update_text_flow(self, ctx: ComponentContext | SlashContext, state_id: str, frame_index: str):
		loc, state, frame_data = await self.basic(ctx, state_id, frame_index)
		if not loc:
			return
		modal = Modal(
		    ParagraphText(
		        custom_id='new_text',
						required=False,
		        value=frame_data.text,
		        label=loc.l('textbox.modal.edit_text.input.label', index=int(frame_index) + 1),
		        placeholder=loc.l('textbox.modal.edit_text.input.placeholder'),
						min_length=0,
		        max_length=get_config("textbox.max-text-length-per-frame", as_str=False)
		    ),
		    custom_id=f'textbox update_text_finish {state_id} {frame_index}',
		    title=loc.l('textbox.modal.edit_text.title', index=int(frame_index) + 1, total=len(state.frames))
		)
		await ctx.send_modal(modal)

	handle_modal_regex = re.compile(r"textbox update_text_finish (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$")

	@modal_callback(handle_modal_regex)
	async def handle_modals(self, ctx: ModalContext, new_text: str):
		match = self.handle_modal_regex.match(ctx.custom_id)
		if len(match.groups()) < 2:
			return ctx.edit_origin()
		state_id, frame_index = match.group("state_id", "frame_index")
		loc, state, frame_data = await self.basic(ctx, state_id, frame_index)
		if not loc:
			return
		old_text = frame_data.text
		frame_data.text = new_text
		if debugging():
			await fancy_message(
					ctx, loc.l('textbox.modal.edit_text.response', new_text=new_text, old_text=old_text), ephemeral=True
			)
		await self.respond(ctx, state_id, frame_index)

	async def respond(self, ctx: SlashContext | ComponentContext | ModalContext, state_id: str, frame_index: int, edit: bool=True, warnings: list  = []):
		loc, state, frame_data = await self.basic(ctx, state_id, frame_index)
		if not loc:
			return
		if warnings is None:
			warnings = []
		files = [await self.render_to_file(ctx, state, frame_preview_index=frame_index)]
		pos = ""
		if len(state.frames) > 2 or frame_index != 0:
			pos = "\n-# "+loc.l("textbox.frame_position", current=int(frame_index)+1, total=len(state.frames))
		if debugging():
			pos += "\n-# **sid**: "+state_id
		next_frame_exists = len(state.frames) != int(frame_index)+1
		print(state)
		embed = Embed(
		    color=Colors.DEFAULT,
		    description=(loc.l("textbox.monologue.char")
		    if frame_data.starting_character_id is None else loc.l("textbox.monologue.face") if frame_data.starting_face_name is None else
		    loc.l("textbox.monologue.press") if frame_data.text else loc.l("textbox.monologue.press_notext"))+pos
		)
		components = [
			ActionRow(
				self.make_characters_select_menu(
					loc, custom_id=f"textbox update_char {state_id} {frame_index}", default=frame_data.starting_character_id
				)
			),
			ActionRow(
				make_empty_select(loc, placeholder=loc.l("textbox.select.faces"))
				if frame_data.starting_face_name is None and frame_data.starting_character_id is None else self.make_faces_select_menu(
					loc,
					custom_id=f"textbox update_face {state_id} {frame_index}",
					character_id=frame_data.starting_character_id,
					default=frame_data.starting_face_name
				)
			),
			ActionRow(
				Button(
					style=ButtonStyle.GRAY,
					label=loc.l("textbox.button.frame.previous"),
					custom_id=f"textbox refresh {state_id} {int(frame_index)-1}",
					disabled=int(frame_index) - 1 < 0
				),
				Button(
					style=ButtonStyle.GRAY if frame_data.text else ButtonStyle.GREEN,
					label=loc.l(f'textbox.button.text.{"edit" if frame_data.text else "add"}'),
					custom_id=f"textbox update_text {state_id} {frame_index}"
				),
				Button(
					style=ButtonStyle.GRAY,
					label=loc.l(f'textbox.button.frame.{"next" if next_frame_exists else "add"}'),
					custom_id=f"textbox refresh {state_id} {int(frame_index)+1}"
				),
			),
			ActionRow(
				Button(
					style=ButtonStyle.GREEN,
					label=loc.l("textbox.button.render"+("&send" if state.options.send_to != 1 else ""), type=loc.l(f"textbox.filetypes.{state.options.out_filetype}")),
					custom_id=f"textbox render {state_id} {frame_index}"
				),
				Button(
					style=ButtonStyle.GREEN,
					label=loc.l("textbox.button.opts"),
					custom_id=f"textbox opts {state_id} {frame_index}"
				)
			)
		]
		if not edit:
			return await ctx.send(embed=embed, components=components, files=files, ephemeral=True)
		elif isinstance(ctx, ComponentContext):
			return await ctx.edit_origin(embed=embed, components=components, files=files)
		else:
			return await ctx.edit(
			    message=ctx.message_id if isinstance(ctx, ModalContext) else "@original",
			    embed=embed,
			    components=components,
			    files=files
			)
	

	int_regex = re.compile(r"^\d+$")
	@textbox.subcommand(sub_cmd_description='Debugging command for textboxes')
	@slash_option(
			name='search',
			description='sid here, special: `all` all states, `user:userid/"me"` user\'s states. at end: `!Page:Amount` (ints)',
			opt_type=OptionType.STRING,
			required=False
	)
	async def state(
	    self,
	    ctx: SlashContext,
	    search: str = "user:me!0:1"
	):
		await fancy_message(ctx, Localization(ctx.locale).l("general.loading"), ephemeral=True)
		states2show: list[tuple[str, State]] = []
		options = search.split("!")
		filter = options[0]

		states2show = states.items()
		match filter:
			case "all":
				pass
			case _:
				if filter.startswith("user:"):
					_ = filter.split(":")
					user_id = _[1] if len(_) == 1 else "me"
					if not self.int_regex.match(user_id) and not user_id == "me":
						await ctx.edit(embeds=Embed(
							color=Colors.BAD,
							title="Invalid user id"
						))
					if user_id == "me":
						user_id = str(ctx.user.id)
					states2show = [a for a in states2show if a[1].owner == int(user_id)]
				elif self.int_regex.match(filter):
					if not filter in states:
						return await ctx.edit(embeds=Embed(
							color=Colors.BAD,
							title=f"Couldn't find sid {filter}"
						))
					states2show = [states[filter]]
		if len(states2show) > 0:
			paging = options[1].split(":")
			page = paging[0] if len(paging) > 0 else "0"
			try:
				page = int(page)
			except:
				return await ctx.edit(embeds=Embed(
					color=Colors.BAD,
					title=f"Invalid Pages (!__{page}__:{items_per_page})"
				))
			items_per_page = paging[1] if len(paging) > 1 else "10"
			try:
				items_per_page = int(items_per_page)
			except:
				return await ctx.edit(embeds=Embed(
					color=Colors.BAD,
					title=f"Invalid items per page (Amount) (!{page}:__{items_per_page}__)"
				))
			if page > len(states2show) * items_per_page:
				return await ctx.edit(embeds=Embed(
					color=Colors.BAD,
					title=f"Page out of bounds, max: {len(states2show)} (!{page}:__{items_per_page}__)"
				))
			states2show = states2show[page*items_per_page:max((page*items_per_page)+items_per_page,len(states2show))]
		if len(states2show) == 0:
			return await ctx.edit(embeds=Embed(
				color=Colors.BAD,
				title="Nothing found" + (" (there are no states)" if len(states) == 0 else " (check your filter maybe?)")
			))
		return await ctx.edit(embeds=Embed(
			color=Colors.DEFAULT,
			title=f"Found results: {len(states2show)}",
			description='\n'.join(map(lambda a: f"-# {a[0]}:\n```{a[1]}```",states2show))
		))