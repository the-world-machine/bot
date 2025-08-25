from typing import Optional, Tuple, Literal, Union, overload
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

	def __init__(self, owner: int, frames: list[Frame] | Frame | None = None, options: StateOptions | None = None):
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
    Retrieves localization, state, and optionally a frame.

    This function is overloaded:
    - If `frame_index` is None, it returns a tuple of (Localization, State).
    - If `frame_index` is provided, it returns a tuple of (Localization, State, Frame).

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

	# Corresponds to the first overload: frame_index is not provided
	if frame_index is None:
		return (loc, state)

	# Corresponds to the second overload: frame_index is provided
	try:
		idx = int(frame_index)
	except ValueError:
		await fancy_message(ctx, loc.l("textbox.errors.invalid_frame_index", index=str(frame_index)), ephemeral=True)
		raise StateShortcutError(f"Frame index '{frame_index}' is not a valid integer.")

	try:
		frame_data: Frame = state.get_frame(idx)
	except IndexError:
		# Special case: allow creating a new frame if the index is exactly one past the end
		if idx == len(state.frames):
			last_frame = state.frames[-1] if state.frames else None
			start_char = last_frame.starting_character_id if last_frame else "default_char_id"
			frame_data = Frame(starting_character_id=start_char)
			state.frames.append(frame_data)  # scary scary scary scary
		else:
			# Any other IndexError is a "frame not found" error
			await fancy_message(ctx, loc.l("textbox.errors.unknown_frame", id=str(frame_index)), ephemeral=True)
			raise StateShortcutError(f"Frame with index '{idx}' not found in state '{state_id}'.")

	return (loc, state, frame_data)


def new_state(state_id, state: State):
	states[state_id] = state
	return states[state_id]
