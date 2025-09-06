import io
from pathlib import Path
from typing import Any, Optional, Tuple, Literal, Union, overload

from interactions import File

from utilities.localization import Localization, assign_variables
from utilities.message_decorations import fancy_message
from utilities.textbox.mediagen import Frame

states = {}
SupportedFiletypes = Literal["WEBP", "GIF", "APNG", "PNG", "JPEG"]
state_template = Path("src/utilities/textbox/template.ttb").read_text()


class StateOptions:
	out_filetype: SupportedFiletypes  # TODO: m,ake this use an enum
	send_to: Literal[1, 2, 3]  # TODO: m,ake this use an enum
	quality: int

	def __init__(
	    self, filetype: SupportedFiletypes = "WEBP", send_to: Literal[1, 2, 3] | str = 1, quality: int | str = 100
	):
		self.out_filetype = filetype
		send_to = int(send_to)  #type:ignore
		if send_to not in (1, 2, 3):
			raise ValueError("send_to must be 1, 2 or 3")
		self.send_to = send_to
		quality = int(quality)
		if quality < 1 or quality > 100:
			raise ValueError("quality must be in the range 1..=100")
		self.quality = quality

	def __repr__(self):
		attrs = { k: getattr(self, k) for k in self.__annotations__ }
		attrs_str = ", ".join(f"{k}={repr(v)}" for k, v in attrs.items())
		return f"StateOptions({attrs_str})"


class State:
	owner: int
	frames: list[Frame]
	options: StateOptions
	memory_leak: Any | None  # 🤑🤑🤑

	def to_string(self, loc: Localization) -> str:
		frames = "\n".join([str(f) for f in self.frames])
		processed: str = assign_variables(
		    state_template,
		    pretty_numbers=False,
		    locale=loc.locale,
		    **{
		        'comment':
		            loc.l(
		                "textbox.ttb.comment",
		                link=
		                f"https://github.com/the-world-machine/bot/tree/main/md/{loc.locale}/textbox/index.md#File_editing"
		            ),
		        'out_filetype':
		            self.options.out_filetype,
		        'send_to':
		            self.options.send_to,
		        'force_send':
		            False,
		        'quality':
		            self.options.quality,
		        'frames':
		            frames
		    }
		)
		return processed

	def from_string(self, input: str, owner: int) -> tuple['State', bool | None]:
		lines = input.split("\n")
		current = ""
		parsed_frames: list[Frame] = []
		StateOptions_parsed = {}
		StateOptions_allowed_keys = [ 'force_send', 'filetype', 'send_to', 'quality']
		for line in lines:
			i += 1
			if line.startswith("#> StateOptions <#"):
				current = "StateOptions"
				continue
			if line.startswith("#> Frames <#"):
				current = "Frames"
				continue
			if line.lstrip().startswith("#"):
				continue
			if current == "Frames":
				try:
					parsed_frames.append(Frame.from_string(line))
				except BaseException as e:
					raise ValueError(f"Failed to parse frame #{len(parsed_frames)} at line {i}! {e}") from e
				continue
			if current == "StateOptions":
				if not '=' in line:
					raise ValueError(f"Couldn't find the value to set at line {i} of StateOptions")
				key, value = line.split("=", maxsplit=1)
				if key not in StateOptions_allowed_keys:
					raise KeyError(
					    f"Received invalid key '{key}' at line {i}, it should be one of: {','.join(StateOptions_allowed_keys)}",
					    ".join(StateOptions_allowed_keys)}"
					)
				StateOptions_parsed[key] = value
				continue

		force_send = StateOptions_parsed.get("force_send", False) == "True"
		return (
		    self.__class__(owner=owner, frames=parsed_frames, options=StateOptions(*StateOptions_parsed)), force_send
		)

	def __init__(
	    self,
	    owner: int,
	    memory_leak: Any | None = None,
	    frames: list[Frame] | Frame | None = None,
	    options: StateOptions | None = None
	):
		self.memory_leak = memory_leak
		self.options = options if options else StateOptions()
		self.owner = owner
		self.frames = []
		if not frames:
			return
		if isinstance(frames, Frame):
			self.frames = [frames]
			return
		if isinstance(frames, list):
			i = 0
			for frame in frames:
				i += 1
				if not isinstance(frame, Frame):
					raise ValueError(f"Frame {i} is not of type Frame.\n{frame}")
				self.frames.append(frame)

	def __repr__(self):
		return (
		    f"State(\n" + f"  owner={self.owner},\n" + f"  frames: len()={len(self.frames)}; [\n" +
		    f"{',\n'.join(f'      {repr(frame)}' for frame in self.frames)}\n" + f"  ]\n" + f"  {self.options}\n"
		    f")"
		)

	def get_frame(self, index: int) -> Frame:
		"""
		Gets a frame from the frames list. Creates an empty frame if the passed index is one above the length of the frames
		
    Raises:
        IndexError: If the passed index is out of bounds and is not length + 1
		"""
		if index < len(self.frames):
			return self.frames[index]
		elif index == len(self.frames):
			frame = Frame()
			self.frames.append(frame)
			return frame
		else:
			raise IndexError(f"Frame #{index} is out of bounds. The state only has {len(self.frames)} frames")


class StateShortcutError(Exception):
	pass


@overload
async def state_shortcut(ctx, state_id: str | int, frame_index: Literal[None]) -> Tuple['Localization', 'State']:
	...


@overload
async def state_shortcut(ctx, state_id: str | int, frame_index: str | int) -> Tuple['Localization', 'State', 'Frame']:
	...


async def state_shortcut(
    ctx, state_id: str | int, frame_index: Optional[str | int]
) -> Union[Tuple['Localization', 'State'], Tuple['Localization', 'State', 'Frame']]:
	"""
		Helper function for textbox to not have to get these variables all the time
    Raises:
        StateShortcutError: If the state or frame cannot be found, or if the
                            frame index is invalid. The user will be notified
                            with an ephemeral message before the exception is raised.
    """
	loc = Localization(ctx)
	try:
		state: State = states[str(state_id)]
	except KeyError:
		await fancy_message(ctx, loc.l("general.errors.expired") + f"\n-# **sid:** {str(state_id)}", ephemeral=True)
		raise StateShortcutError(f"State with ID '{state_id}' not found.")

	if frame_index is None:
		return (loc, state)

	try:
		idx = int(frame_index)
	except ValueError:
		await fancy_message(ctx, loc.l("textbox.errors.invalid_frame_index", index=str(frame_index)), ephemeral=True)
		raise StateShortcutError(f"Frame index '{frame_index}' is not a valid integer.")

	try:
		frame_data: Frame = state.get_frame(idx)
	except IndexError:
		if idx == len(state.frames):
			state.frames.append(Frame())  # scary scary scary scary
		else:
			await fancy_message(ctx, loc.l("textbox.errors.unknown_frame", id=str(frame_index)), ephemeral=True)
			raise StateShortcutError(f"Frame with index '{idx}' not found in state '{state_id}'.")

	return (loc, state, frame_data)


def new_state(state_id, state: State):
	states[state_id] = state
	return states[state_id]
