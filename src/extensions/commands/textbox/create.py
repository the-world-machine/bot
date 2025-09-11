import io
import re
import asyncio
from interactions.models.discord.components import (
	FileComponent,
	MediaGalleryItem,
	UnfurledMediaItem,
	ContainerComponent,
	TextDisplayComponent,
	MediaGalleryComponent,)
from datetime import datetime
from typing import Any, Literal, get_args
from utilities.misc import SortOption, optionSearch
from .facepic_selector import set_facepic_in_frame_text
from utilities.config import debugging, get_config
from utilities.localization import Localization, put_mini
from utilities.message_decorations import Colors, fancy_message
from utilities.textbox.mediagen import Frame, SupportedFiletypes, render_textbox_frames
from utilities.textbox.states import StateShortcutError, State, StateOptions, new_state, state_shortcut
from interactions import ActionRow, AutocompleteContext, Button, ButtonStyle, ComponentContext, Embed, File, MessageFlags, Modal, ModalContext, OptionType, ParagraphText, SlashCommandChoice, SlashContext, component_callback, modal_callback, slash_option, AllowedMentions

from utilities.textbox.facepics import f_storage
nomentions = AllowedMentions(parse=[])


@slash_option(
		name='text',
		description='What you want the character to say?',
		opt_type=OptionType.STRING,
		required=False,
		max_length=int(get_config("textbox.max-text-length-per-frame", typecheck=int))
)
@slash_option(
		name='facepic',
		argument_name='face_path',
		description="Which facepic do you want on the textbox? (type another / at the end for more options)",
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
async def command(
		self, 
		ctx: SlashContext,
		text: str = "",
		face_path: str | None = None,
		animated: bool | None = None,
		filetype: SupportedFiletypes | None = None,
		send_to: Literal[1, 2, 3] = 1
):
	await respond(ctx, type='loading')
	state_id = str(ctx.id)  # state_id is the initial `/textbox create` interaction's id
	erored = False

	if animated != None:
		filetype = 'WEBP' if animated else 'PNG'
	if not filetype:
		filetype = 'WEBP'

	if filetype not in get_args(SupportedFiletypes):
		return

	if face_path:
		text = set_facepic_in_frame_text(text, face_path)

	# init state
	new_state(state_id, State(
		owner=ctx.user.id,
		memory_leak=ctx,
		options=StateOptions(
			filetype=filetype,
			send_to=send_to
		),
		frames=Frame(text=text)
	))
	
	if send_to != 1 and (len(text) != 0 and face_path != None):
		await send_output(ctx, state_id, 0)

	await respond(ctx, state_id, 0, edit=not erored)

async def facepic_autocomplete(self, ctx: AutocompleteContext):
	loc = Localization(ctx)
	search_query = ctx.input_text
	print(search_query)
	tøp = []
	print(search_query, type(search_query))
	if not search_query or search_query == "":
		tøp.append(SlashCommandChoice(name="Start by selecting a folder (focus back on input to continue)", value="Other/"))
	choices: list[SortOption] = []
	#optionSearch(search_query, [SortOption(picked_name=name, value=name) for name, char in characters])
	path = [part for part in search_query.strip().split("/") if part != ""]
	selected_item = f_storage.facepics
	if not search_query == "":
		for part in path:
			selected_item = selected_item.get(part)
			if selected_item is None:
				return await ctx.send([SlashCommandChoice(name="No facepics found for this search", value="")])
	if selected_item:
		for key, value in selected_item.items():
			if key.startswith("__"):
				continue
			full_path = "/".join(path + [key])
			if isinstance(value, dict):
				choices.append(SortOption(picked_name=full_path+"/", value=full_path))
			else:
				choices.append(SortOption(picked_name=full_path, value=full_path))
	top = tøp[:5]
	return await ctx.send(tøp + optionSearch(search_query, choices, 25-len(tøp)))

handle_components_regex = re.compile(
		r"textbox (?P<method>refresh|render|change_text|facepic_selector|delete_frame|edit) (?P<state_id>-?\d+) (?P<frame_index>-?\d+)$"
)

@component_callback(handle_components_regex)
async def handle_components(self, ctx: ComponentContext):
	match = handle_components_regex.match(ctx.custom_id)
	if match:
		a = match.groups()
		lena = len(a)
	if match == None or lena != 3:
		return ctx.edit_origin()
	method, state_id, frame_index = match.group("method", "state_id", "frame_index")
	try:
		loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
	except StateShortcutError:
		return
	
	match method:
		case "change_text":
			return await init_change_text_flow(ctx, state_id, frame_index)
		case "delete_frame":
			del state.frames[int(frame_index)]
		case "edit":
			return await init_edit_flow(ctx, state_id, frame_index)
		case "render":
			await send_output(ctx, state_id, int(frame_index))
			
	await respond(ctx, state_id, int(frame_index))

async def send_output(ctx: ComponentContext | SlashContext, state_id: str, frame_index: int):
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
	file = await render_to_file(ctx, state)
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

async def render_to_file(ctx: ComponentContext|SlashContext|ModalContext, state: State, frame_preview_index: int | None = None) -> File:
	loc = Localization(ctx)

	frames = state.frames
	filetype = state.options.out_filetype 

	if frame_preview_index is not None:
		filetype = "PNG"
		frames = [state.frames[int(frame_preview_index)]]
	filename = loc.l(f"textbox.alt.{'single' if frame_preview_index != None else 'multi'}_frame.filename", frames=len(frames), timestamp=str(round(datetime.now().timestamp())))

	buffer = await render_textbox_frames(frames, state.options.quality, filetype)
	buffer.seek(0)
	filename = filename + ("" if filetype == "APNG" else "."+filetype)

	#	TODO: alt text
	return File(file=buffer, file_name=filename)#, description=alt_text if alt_text else frame.text)



async def init_change_text_flow(ctx: ComponentContext | SlashContext, state_id: str, frame_index: str):
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
	match = update_text_modal_regex.match(ctx.custom_id)
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
	await respond(ctx, state_id, int(frame_index))

async def init_edit_flow(ctx: ComponentContext | SlashContext, state_id: str, frame_index: str):
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
	await respond(ctx, state_id, int(frame_index))


async def respond(ctx: SlashContext | ComponentContext | ModalContext, state_id: str | None = None, frame_index: int | None = None, type: Literal['normal', 'loading']="normal", edit: bool=True, warnings: list = []):

	if type == "loading":
		return await fancy_message(ctx, components=[ContainerComponent(TextDisplayComponent(content=Localization(ctx).l("generic.loading")), accent_color=Colors.DEFAULT.value)], ephemeral=True)
	
	assert state_id is not None and frame_index is not None
	
	try:
		loc, state, frame_data = await state_shortcut(ctx, state_id, frame_index)
	except StateShortcutError:
		return

	if warnings is None:
		warnings = []
	status = ""
	pos = ""
	if len(state.frames) > 1 or frame_index != 0:
		pos = f"\n-# {loc.l("textbox.frame_position", current=int(frame_index)+1, total=len(state.frames))}"
	if debugging():
		pos += "\n-# **sid**: "+state_id
	next_frame_exists = len(state.frames) != int(frame_index)+1
	print(state)
	
	
	preview = await render_to_file(ctx, state, frame_preview_index=int(frame_index))
	assert preview.file_name is not None
	funny_name = (lambda p: re.sub(r'[^a-zA-Z0-9]+', '_', preview.file_name[:p]).strip('_') + preview.file_name[p:] if p > 0 else re.sub(r'[^a-zA-Z0-9]+', '_', preview.file_name).strip('_'))(preview.file_name.rfind('.')) # type: ignore
	tbb = File(file=io.BytesIO(state.to_string(loc).encode('utf-8')), file_name=funny_name.rsplit(".",maxsplit=1)[0]+".backup.tbb")
	files = [tbb, preview]
	components = [
		FileComponent(
			file=UnfurledMediaItem(url=f"attachment://{tbb.file_name}")
		),
		MediaGalleryComponent(items=[
			MediaGalleryItem(
				media=UnfurledMediaItem(url=f"attachment://{funny_name}")
			),
		]),
		ActionRow(
			Button(
				style=ButtonStyle.BLURPLE,
				label=loc.l(f'textbox.button.text.{"edit" if frame_data.text else "add"}'),
				custom_id=f"textbox change_text {state_id} {frame_index}"
			),
			Button(
				style=ButtonStyle.BLURPLE,
				label=loc.l(f'textbox.button.face'),
				custom_id=f"textbox_fs init {state_id} {frame_index}"
			),
			Button(
				style=ButtonStyle.BLURPLE,
				label=loc.l(f'textbox.button.edit'),
				custom_id=f"textbox edit {state_id} {frame_index}"
			),
		),
		ContainerComponent(
			TextDisplayComponent(content=pos),
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
		return await ctx.send(components=components, files=files, ephemeral=True)
	elif isinstance(ctx, ComponentContext):
		return await ctx.edit_origin(components=components, files=files)
	else:
		return await ctx.edit(
				message=ctx.message_id if isinstance(ctx, ModalContext) else "@original",
				components=components,
				files=files
		)
	