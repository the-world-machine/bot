import asyncio
from datetime import datetime
import re
from typing import Literal, get_args
from interactions import ActionRow, AutocompleteContext, Button, ButtonStyle, ComponentContext, Embed, Extension, File, MessageFlags, Modal, ModalContext, OptionType, ParagraphText, SlashCommandChoice, SlashContext, StringSelectMenu, StringSelectOption, component_callback, contexts, integration_types, modal_callback, slash_command, slash_option, AllowedMentions
from interactions.models.discord.components import (
	MediaGalleryComponent,
	MediaGalleryItem,
	TextDisplayComponent,
	ContainerComponent,
	SeparatorComponent,
	ThumbnailComponent,
	UnfurledMediaItem,
)
from utilities.config import debugging, get_config
from utilities.textbox.mediagen import Frame, SupportedFiletypes, render_textbox_frames
from utilities.localization import Localization, put_mini
from utilities.message_decorations import Colors, fancy_message
from utilities.misc import SortOption, make_empty_select, optionSearch
from utilities.textbox.characters import get_character, get_characters
from utilities.textbox.states import StateShortcutError, states, State, StateOptions, new_state, state_shortcut
nomentions = AllowedMentions(parse=[])

class TextboxCommands(Extension):
	global states

	@staticmethod
	def make_characters_select_menu(
	    loc: Localization = Localization(), default: str | None = None, custom_id: str = "textbox update_char 0"
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
	    character_id: str | None = None,
	    custom_id: str = "textbox update_face 0 0",
	    default: str | None = None
	):
		try:
			character = get_character(character_id) # type: ignore
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
			max_length=int(get_config("textbox.max-text-length-per-frame", typecheck=int))
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
	    text: str | None = None,
	    character_id: str | None = None,
	    face_name: str | None = None,
	    animated: bool | None = None,
			filetype: SupportedFiletypes | None = None,
	    send_to: Literal[1, 2, 3] = 1
	):
		await self.respond(ctx, type='loading')
		state_id = str(ctx.id)  # state_id is the initial `/textbox create` interaction's id, need to save these between restarts later somehow
		loc = Localization(ctx)
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
		# Correct version:
		if filetype not in get_args(SupportedFiletypes):
			return
		# init state
		new_state(state_id, State(
			owner=ctx.user.id,
			options=StateOptions(
				filetype=filetype,
				send_to=send_to
			),
			frames=Frame(text=text, starting_character_id=character_id, starting_face_name=face_name)
		))

		if send_to != 1 and character_id and face_name:
			# if user specified enough params to send the textbox right after the /command...
			await self.send_output(ctx, state_id, 0)

		await self.respond(ctx, state_id, 0, edit=not erored)

	@create.autocomplete("character")
	async def character_autocomplete(self, ctx: AutocompleteContext):
		loc = Localization(ctx)
		characters = get_characters()
		choices = optionSearch(ctx.input_text, [SortOption(picked_name=name, value=name) for name, char in characters])

		return await ctx.send(choices[:25])
	
	@create.autocomplete("face")
	async def face_autocomplete(self, ctx: AutocompleteContext):
		loc = Localization(ctx)
		character = get_character(ctx.kwargs["character"] if "character" in ctx.kwargs else "Other")
		choices = optionSearch(ctx.input_text, [SortOption(picked_name=name, value=name) for name in character.get_face_list()])
		
		return await ctx.send(choices[:25])
	
	handle_components_regex = re.compile(
	    r"textbox (?P<method>refresh|render|update_(char|face|text)|delete_frame|edit) (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$"
	)

	@component_callback(handle_components_regex)
	async def handle_components(self, ctx: ComponentContext):
		match = self.handle_components_regex.match(ctx.custom_id)
		if match == None or len(match.groups()) <= 3:
			return ctx.edit_origin()
		method, state_id, frame_index = match.group("method", "state_id", "frame_index")
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return
		match method:
			case "update_char":
				frame_data.starting_character_id = ctx.values[0]
				frame_data.starting_face_name = None
			case "update_face":
				frame_data.starting_face_name = ctx.values[0]
			case "update_text":
				return await self.init_update_text_flow(ctx, state_id, frame_index)
			case "delete_frame":
				del state.frames[int(frame_index)]
			case "edit":
				return await self.init_edit_flow(ctx, state_id, frame_index)
			case "render":
				await self.send_output(ctx, state_id, int(frame_index))
				
		await self.respond(ctx, state_id, int(frame_index))

	async def send_output(self, ctx: ComponentContext | SlashContext, state_id: str, frame_index: int):
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return
		pos = ""
		message = await ctx.respond(
			embed=Embed(
				description=loc.l("textbox.monologue.rendering")+pos, 
				color=Colors.DARKER_WHITE
			),
			ephemeral=True,
		)

		start=datetime.now()
		file = await self.render_to_file(ctx, state)
		end=datetime.now()
		took=start-end

		asyncio.create_task(ctx.edit(message=message, embed=Embed(description=loc.l("textbox.monologue.sending")+pos, color=Colors.DARKER_WHITE)))
		content = f"-# [ {ctx.user.mention} ]"
		
		try:
			if state.options.send_to == 3:
				if ctx.guild:
					sent_message = await ctx.channel.send(
						content=content, files=file, allowed_mentions=nomentions
					)
				else:
					sent_message = await ctx.send(content=content, files=file, allowed_mentions=nomentions)
			elif state.options.send_to == 2:
				sent_message = await ctx.author.send(files=file)
			elif state.options.send_to == 1:
				sent_message = await ctx.send(content=content, files=file, allowed_mentions=nomentions, ephemeral=True)
		except: # when it fails to send a dm or a followup to an ephemeral message with a non-ephemeral message
			return await ctx.edit(message=message, embed=Embed(description=loc.l("textbox.errors.failed_to_send"+("_dm" if state.options.send_to == 3 else "")), color=Colors.DARKER_WHITE))
		desc = loc.l("textbox.monologue.done")
		if debugging():
			desc+="\n-# "+loc.l("textbox.monologue.debug", time=took.total_seconds(), sid=state_id)
		if state.options.out_filetype in ("WEBP", "GIF", "APNG") and sent_message and MessageFlags.EPHEMERAL in sent_message.flags:
			mini = await put_mini(loc, "textbox.errors.ephemeral_warnote", ctx.user.id, type="warn")
			if mini != "":
				await ctx.edit(message=sent_message, content=f"{sent_message.content}\n{mini}", allowed_mentions=nomentions)
		return await ctx.edit(message=message, embed=Embed(description=desc, color=Colors.DEFAULT))

	async def render_to_file(self, ctx: ComponentContext|SlashContext|ModalContext, state: State, frame_preview_index: int | None = None) -> File:
		# you do alt text here later dont unabstract this
		loc = Localization(ctx)

		frames = state.frames
		if frame_preview_index != None:
			frame = state.frames[int(frame_preview_index)]
			frames = [state.frames[int(frame_preview_index)]]
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
			for frame in state.frames:
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
		buffer = await render_textbox_frames(frames, state.options.quality, state.options.out_filetype if frame_preview_index is None else "PNG")
		_filetype="."+state.options.out_filetype
		if frame_preview_index is not None:
			_filetype = ".PNG"
		if state.options.out_filetype == "APNG":
			_filetype = ""
		filename = filename + _filetype
		buffer.seek(0)
		return File(file=buffer, file_name=filename)#, description=alt_text if alt_text else frame.text)



	async def init_update_text_flow(self, ctx: ComponentContext | SlashContext, state_id: str, frame_index: str):
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return
		modal = Modal(
		    ParagraphText(
		        custom_id='new_text',
						required=False,
		        value=frame_data.text,
		        label=loc.l('textbox.modal.edit_text.input.label', index=int(frame_index) + 1),
		        placeholder=loc.l('textbox.modal.edit_text.input.placeholder'),
						min_length=0,
		        max_length=get_config("textbox.max-text-length-per-frame", typecheck=int)
		    ),
		    custom_id=f'textbox update_text_finish {state_id} {frame_index}',
		    title=loc.l('textbox.modal.edit_text.title', index=int(frame_index) + 1, total=len(state.frames))
		)
		await ctx.send_modal(modal)

	update_text_modal_regex = re.compile(r"textbox update_text_finish (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$")

	@modal_callback(update_text_modal_regex)
	async def handle_update_text_modal(self, ctx: ModalContext, new_text: str):
		match = self.update_text_modal_regex.match(ctx.custom_id)
		if match == None or len(match.groups()) < 2:
			return
		state_id, frame_index = match.group("state_id", "frame_index")
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return
		old_text = frame_data.text
		frame_data.text = new_text
		if debugging():
			await fancy_message(
					ctx, loc.l('textbox.modal.edit_text.response', new_text=new_text, old_text=old_text), ephemeral=True
			)
		await self.respond(ctx, state_id, int(frame_index))



	async def init_edit_flow(self, ctx: ComponentContext | SlashContext, state_id: str, frame_index: str):
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return
		frames = ""
		for frame in state.frames:
			frames += str(frame)+"\n"
		modal = Modal(
		    ParagraphText(
		        custom_id='updated_frames',
						required=False,
		        value=frames,
		        label=loc.l('textbox.modal.edit_frames.input.label', index=int(frame_index) + 1),
		        placeholder=loc.l('textbox.modal.edit_frames.input.placeholder'),
		    ),
		    custom_id=f'textbox edit_finish {state_id} {frame_index}',
		    title=loc.l('textbox.modal.edit_frames.title', index=int(frame_index) + 1, total=len(state.frames))
		)
		await ctx.send_modal(modal)

	edit_regex = re.compile(r"textbox edit_finish (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$")

	@modal_callback(edit_regex)
	async def handle_edit_modal(self, ctx: ModalContext, updated_frames: str):
		match = self.edit_regex.match(ctx.custom_id)
		if match == None or len(match.groups()) < 2:
			return
		state_id, frame_index = match.group("state_id", "frame_index")
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return
		old_frames = ""
		for frame in state.frames:
			old_frames += str(frame)+"\n"
		try:
			new_frames = [Frame.from_string(raw) for raw in updated_frames.split("\n")]
		except BaseException as e:
			return await ctx.send(f"Woopsie! {e}", ephemeral=True)
		state.frames = new_frames
		# if debugging():
		# 	await fancy_message(
		# 			ctx, loc.l('textbox.modal.edit_frames.response', new_text=new_text, old_text=old_text), ephemeral=True
		# 	)
		await self.respond(ctx, state_id, int(frame_index))


	async def respond(self, ctx: SlashContext | ComponentContext | ModalContext, state_id: str | None = None, frame_index: int | None = None, type: Literal['normal', 'loading']="normal", edit: bool=True, warnings: list = []):
		if type == "loading":
			return await fancy_message(ctx, components=[ContainerComponent(TextDisplayComponent(content=Localization(ctx).l("generic.loading")), accent_color=Colors.DEFAULT.value)], ephemeral=True)
		
		assert state_id is not None and frame_index is not None
		
		try:
			loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
		except StateShortcutError:
			return

		if warnings is None:
			warnings = []
		pos = ""
		if len(state.frames) > 1 or frame_index != 0:
			pos = f"\n-# {loc.l("textbox.frame_position", current=int(frame_index)+1, total=len(state.frames))}"
		if debugging():
			pos += "\n-# **sid**: "+state_id
		next_frame_exists = len(state.frames) != int(frame_index)+1
		print(state)
		
		
		preview = await self.render_to_file(ctx, state, frame_preview_index=int(frame_index))
		assert preview.file_name is not None
		funny_name = (lambda p: re.sub(r'[^a-zA-Z0-9]+', '_', preview.file_name[:p]).strip('_') + preview.file_name[p:] if p > 0 else re.sub(r'[^a-zA-Z0-9]+', '_', preview.file_name).strip('_'))(preview.file_name.rfind('.')) # type: ignore
		components = [
			MediaGalleryComponent(items=[
				MediaGalleryItem(
					media=UnfurledMediaItem(url=f"attachment://{funny_name}")
				)
			]),
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
					style=ButtonStyle.BLURPLE,
					label=loc.l(f'textbox.button.text.{"edit" if frame_data.text else "add"}'),
					custom_id=f"textbox update_text {state_id} {frame_index}"
				),
				Button(
					style=ButtonStyle.BLURPLE,
					label=loc.l(f'textbox.button.edit'),
					custom_id=f"textbox edit {state_id} {frame_index}"
				),
				
			),
			ContainerComponent(
				TextDisplayComponent(content=f'{(loc.l("textbox.monologue.char")
		    if frame_data.starting_character_id is None else loc.l("textbox.monologue.face") if frame_data.starting_face_name is None else
		    loc.l("textbox.monologue.press") if frame_data.text else loc.l("textbox.monologue.press_notext"))}{pos}'),
				ActionRow(
					Button(
						style=ButtonStyle.GRAY,
						label=loc.l("textbox.button.frame.previous"),
						custom_id=f"textbox refresh {state_id} {int(frame_index)-1}",
						disabled=int(frame_index) - 1 < 0
					),
					Button(
						style=ButtonStyle.GREEN,
						label=loc.l("textbox.button.render"+("send" if state.options.send_to != 1 else ""), type=loc.l(f"textbox.filetypes.{state.options.out_filetype}")),
						custom_id=f"textbox render {state_id} {frame_index}"
					),
					Button(
						style=ButtonStyle.DANGER if frame_data.text else ButtonStyle.GRAY,
						label=loc.l(f'textbox.button.frame.{"clear" if len(state.frames) == 1 else "delete"}'),
						custom_id=f"textbox delete_frame {state_id} {frame_index}"
					),
					Button(
						style=ButtonStyle.GRAY,
						label=loc.l(f'textbox.button.frame.{"next" if next_frame_exists else "add"}'),
						custom_id=f"textbox refresh {state_id} {int(frame_index)+1}"
					),
				)
			)
		]

		if not edit:
			return await ctx.send(components=components, file=preview, ephemeral=True)
		elif isinstance(ctx, ComponentContext):
			return await ctx.edit_origin(components=components, file=preview)
		else:
			return await ctx.edit(
			    message=ctx.message_id if isinstance(ctx, ModalContext) else "@original",
			    components=components,
			    file=preview
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
		await fancy_message(ctx, Localization(ctx).l("generic.loading"), ephemeral=True)
		states2show: list[tuple[str, State]] = []
		options = search.split("!")
		filter = options[0]

		states2show = list(states.items())
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
			items_per_page = "10"
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