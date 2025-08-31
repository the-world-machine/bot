import io
import apng
import inspect
import textwrap
from pathlib import Path
from grapheme import graphemes
from interactions import Color
from utilities.misc import cached_get
from utilities.config import get_config
from dataclasses import dataclass, field, fields
from PIL import Image, ImageDraw, ImageFont
from typing import Any, Callable, Literal, get_args, Sequence, get_origin

from utilities.textbox.facepics import get_facepic
from utilities.textbox.parsing import FacepicChangeCommand, parse_textbox_text

SupportedFiletypes = Literal["WEBP", "GIF", "APNG", "PNG", "JPEG"]
SupportedLocations = Literal["aleft", "acenter", "aright", "left", "center", "right", "bleft", "bcenter", "bright"]
sanitize: Callable[[str], str] = lambda text: text.replace('\\', '\\\\').replace('\n', '\\n')
desanitize: Callable[[str], str] = lambda text: text.replace('\\n', '\n').replace('\\\\', '\\')


class SerializableData:
	_separator: str = ';'

	def __str__(self) -> str:
		"""Serializes the object to a string based on its fields."""
		parts = []
		for field in fields(self):  # type: ignore
			value = getattr(self, field.name)
			parts.append(str(value))
		return self._separator.join(parts)

	@classmethod
	def from_string(cls, data_string: str):
		"""Deserializes a string into an object of this class."""

		class_fields = fields(cls)  # type: ignore
		num_expected = len(class_fields)

		parts = data_string.split(cls._separator, num_expected - 1)

		if len(parts) != num_expected:
			raise ValueError(
			    f"Invalid format for {cls.__name__}. Expected {num_expected} parts separated by '{cls._separator}', but got {len(parts)} in '{data_string}'"
			)

		kwargs = {}
		for field, value_str in zip(class_fields, parts):
			kwargs[field.name] = cls._parse_value(value_str, field.type)

		return cls(**kwargs)

	@staticmethod
	def _parse_value(value_str: str, target_type: Any) -> Any:
		"""Helper to parse a string value into its target Python type."""
		origin = get_origin(target_type)
		args = get_args(target_type)

		if origin is Literal:
			if value_str not in args:
				raise ValueError(f"Value '{value_str}' is not a valid choice from {args}")
			return value_str
		if origin in (list, tuple):
			if not value_str:
				return origin()
			item_type = args[0] if args else str
			return origin(SerializableData._parse_value(item.strip(), item_type) for item in value_str.split(','))
		if origin is not None and any(
		    isinstance(arg, type) and issubclass(arg, type(None)) for arg in args
		):  # Handles X | None
			if value_str == 'None':
				return None
			actual_type = next(arg for arg in args if not issubclass(arg, type(None)))
			return SerializableData._parse_value(value_str, actual_type)

		if target_type is bool:
			if value_str in ('True', 'true', '+', 'yes'):
				return True
			if value_str == ('False', 'false', '-', 'no'):
				return False
			raise ValueError(f"couldn't parse '{value_str}' as bool.")
		if target_type is int:
			return int(value_str)
		if target_type is str:
			return value_str

		if inspect.isclass(target_type) and issubclass(target_type, SerializableData):
			return target_type.from_string(value_str)

		return target_type(value_str)


@dataclass
class BackgroundStyle(SerializableData):
	source: str = "OneShot"

	_separator: str = '-'


# future stuffff -- [
#color: Color = Color(color="#ff6600")


@dataclass
class NameStyle(SerializableData):
	source: str = "OneShot"
	position: SupportedLocations = "right"
	color: Color = Color(color="#ff6600")

	_separator: str = '-'


@dataclass
class FacepicStyle(SerializableData):
	source: str = "OneShot"
	face_position: SupportedLocations = "left"

	_separator: str = '-'


# ] --


@dataclass
class FrameOptions(SerializableData):
	background: BackgroundStyle = field(default_factory=BackgroundStyle)
	animated: bool = True
	starting_speed: float = 1.0
	end_delay: int = 150
	end_arrow_bounces: int = 4
	end_arrow_delay: int = 150
	static_delay_override: int | None = None

	_separator: str = ';'


@dataclass
class Frame(SerializableData):
	text: str | None = None
	options: FrameOptions = field(default_factory=FrameOptions)

	_separator: str = ';'

	def __str__(self):
		return f"{{{self.options}}};{sanitize(self.text or '')}"

	@classmethod
	def from_string(cls, frame_string: str):
		try:
			if not frame_string.startswith('{'):
				raise ValueError("String must start with '{' for options.")

			end_brace_idx = frame_string.find('}')
			if end_brace_idx == -1:
				raise ValueError("Mismatched braces: missing '}'.")

			if len(frame_string) <= end_brace_idx + 1 or frame_string[end_brace_idx + 1] != cls._separator:
				raise ValueError(f"Options block must be followed by a '{cls._separator}'.")

			options_raw = frame_string[1:end_brace_idx]
			sanitized_text = frame_string[end_brace_idx + 2:]

			options = FrameOptions.from_string(options_raw)
			text = desanitize(sanitized_text) if sanitized_text else None

			return cls(options=options, text=text)
		except (ValueError, IndexError) as e:
			raise ValueError(
			    f"Invalid Frame format. Expected '{{options}}{cls._separator}text', but got '{frame_string}'"
			) from e


async def render_frame(frame: Frame, animated: bool = True) -> tuple[list[Image.Image], list[int]]:
	background = Image.open(await cached_get(Path("src/data/images/textbox/backgrounds/", "normal.png")))
	burned_background = background.copy()

	font = ImageFont.truetype(await cached_get(Path(get_config("textbox.font")), force=True), 20)
	text = Image.new("RGBA", (background.width, background.height), color=(255, 255, 255, 0))
	text_x, text_y = 20, 17
	text_width = background.width - (20 * 2)
	text_height = background.height - (17 * 2)
	images: list[Image.Image] = []
	durations: Sequence[int] = []

	def put_frame(duration: int):
		new = burned_background.copy()
		new.paste(text, (text_x, text_y), mask=text)
		images.append(new)
		durations.append(duration)

	facepic_present = False

	async def set_facepic(command: FacepicChangeCommand, delay: bool = False):
		nonlocal burned_background
		nonlocal facepic_present
		nonlocal text_width
		burned_background = background.copy()
		facepic = await get_facepic(command.facepic)
		if facepic:
			facepic_present = True
			facepic = await facepic.get_image(size=96)
			facepic = facepic.resize((96, 96), resample=0)
			burned_background.paste(facepic, (496, 16), mask=facepic.convert("RGBA"))
		else:
			facepic_present = False
		if facepic_present and facepic:
			text_width = background.width - (20 * 2) - facepic.width + 10
		else:
			text_width = background.width - (20 * 2)
		if delay and animated:
			put_frame(1)

	parsed = parse_textbox_text(frame.text) if frame.text else []
	text_offset = [ 0.0, 0.0 ]
	for i in range(0, len(parsed)):
		command = parsed[i]
		if isinstance(command, FacepicChangeCommand):
			await set_facepic(command)

		elif isinstance(command, str):
			message = command
			d = ImageDraw.Draw(text)
			cumulative_text = ""

			for cluster in list(graphemes(message)):  # type: ignore
				if not cluster:
					cluster: str = ""
				cumulative_text += cluster
				duration = 20
				match cluster:
					case '\n':
						duration = 800
					case '.' | '!' | '?' | '．' | '？' | '！':
						duration = 200
					case ',' | '，':
						duration = 40
				d.text((text_offset[0], text_offset[1]), cluster, font=font, fill=(255, 255, 255))
				text_offset[0] += 15.0
				if text_y + text_offset[1] > background.height - (17 * 2):
					text_y -= 25
				if text_offset[0] + 15 > text_width:
					text_offset[1] += 25.0
					text_offset[0] = 15.0
				if animated:
					put_frame(duration)
	put_frame(0)
	return (images, durations)


# >>> bounce(2, 3)
# [1, 2, 3, 2, 1, 2, 3, 2, 1]
def bounce(times, height=3):
	pattern = []
	length = ((height + (height - 2)) * times) + 1
	cycle_length = (height * 2) - 2

	for i in range(length):
		position = i % cycle_length

		if position < height:
			value = position + 1
		else:
			value = (cycle_length - position) + 1

		pattern.append(value)

	return pattern


async def render_textbox_frames(
    frames: list[Frame],
    quality: int = 80,
    filetype: SupportedFiletypes = "WEBP",
    frame_index: int | None = None
) -> io.BytesIO:
	all_images: list[Image.Image] = []
	all_durations: list[int] = []
	buffer = io.BytesIO()
	if filetype in ("JPEG", "PNG"):
		if not frame_index:
			print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
			frame_index = 0
		frame = frames[int(frame_index)]
		image = (await render_frame(frame, False))[0][0]
		if filetype == "JPEG":
			buffer = io.BytesIO()
			if image.mode == 'RGBA':
				rgb_image = Image.new('RGB', image.size, (255, 255, 255))
				rgb_image.paste(image, mask=image.split()[3])
				rgb_image.save(buffer, format="JPEG", quality=quality)
			else:
				image.save(buffer, format="JPEG", quality=quality)
		else:
			image.save(
			    buffer,
			    format="PNG",
			    compress_level=9 - int(max(0, min(100, quality)) * 9 / 100)  #  quality = 0->100 = compress_level = 9->0
			)
		return buffer

	for frame in frames:

		images, durations = await render_frame(frame, frame.options.animated)
		all_images.extend(images)
		all_durations.extend(durations)

		# make the ending thing
		arrow = Image.open(await cached_get(Path("src/data/images/textbox/backgrounds/", "normal_arrow.png")))
		arrow_rgba = arrow.convert('RGBA')
		last_frame = all_images[-1]
		all_durations[-1] = frame.options.end_delay
		bounce_frames = [
		    ":3",
		    last_frame.copy(),
		    last_frame.copy(),
		    last_frame.copy(),
		]
		bounce_frames[1].paste(arrow, (299, 119), arrow_rgba)
		bounce_frames[2].paste(arrow, (299, 119 - 1), arrow_rgba)
		bounce_frames[3].paste(arrow, (299, 119 - 2), arrow_rgba)

		for i in bounce(frame.options.end_arrow_bounces, 3):
			all_images.append(bounce_frames[i])
			all_durations.append(frame.options.end_arrow_delay)
	all_images.append(last_frame.copy())
	all_durations.append(150)
	match filetype:
		case "WEBP":
			all_images[0].save(
			    buffer,
			    format="WEBP",
			    save_all=True,
			    append_images=all_images[1:],
			    duration=all_durations,
			    quality=quality
			)
		case "APNG":
			png_images = []
			for img in all_images:
				temp_buffer = io.BytesIO()
				img.save(temp_buffer, format="PNG")
				temp_buffer.seek(0)
				png_obj = apng.PNG.from_bytes(temp_buffer.getvalue())
				png_images.append(png_obj)

			animation = apng.APNG()

			for i, png_obj in enumerate(png_images):
				animation.append(png_obj, delay=int(all_durations[i]), delay_den=1000)

			apng_bytes = animation.to_bytes()
			buffer = io.BytesIO(apng_bytes)
		case "GIF":
			all_images[0].save(
			    buffer,
			    format="GIF",
			    save_all=True,
			    append_images=all_images[1:],
			    duration=all_durations,
			)
	buffer.seek(0)
	return buffer


# import asyncio

# test_frames = {
#     0: Frame(character_id="Niko", face_name="Normal", text="Hello! 👋"),
#     1: Frame(character_id="Niko", face_name="Upset", text="nuclear Explosion!!!!!!!!!!!!!!!!!!!!!!"),
#     2: Frame(character_id="Kip", face_name="Normal", text="...And so the...."),
# }

# async def test():
# 	buffer = await render_textboxes(test_frames)
# 	with open("testbox.webp", "wb") as f:
# 		f.write(buffer.getvalue())

# asyncio.run(test())
