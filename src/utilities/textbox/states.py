from typing import Any, Optional, Tuple, Literal, Union, overload
from utilities.localization import Localization
from utilities.message_decorations import fancy_message
from utilities.textbox.mediagen import Frame

states = {}
SupportedFiletypes = Literal["WEBP", "GIF", "APNG", "PNG", "JPEG"]


class StateOptions:
	out_filetype: SupportedFiletypes  # TODO: m,ake this use an enum
	send_to: Literal[1, 2, 3]  # TODO: m,ake this use an enum
	quality: int

	def __init__(self, filetype: SupportedFiletypes = "WEBP", send_to: Literal[1, 2, 3] = 1, quality: int = 100):
		self.out_filetype = filetype
		self.send_to = send_to
		self.quality = quality

	def __repr__(self):
		attrs = { k: getattr(self, k) for k in self.__annotations__ }
		attrs_str = ", ".join(f"{k}={repr(v)}" for k, v in attrs.items())
		return f"StateOptions({attrs_str})"


class State:
	owner: int
	frames: list[Frame]
	options: StateOptions
	memory_leak: Any  # 🤑🤑🤑

	def __init__(
	    self,
	    owner: int,
	    memory_leak: Any,
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

	def get_frame(self, index: int):
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
		await fancy_message(ctx, loc.l("textbox.errors.unknown_state", id=str(state_id)), ephemeral=True)
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
