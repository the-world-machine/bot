import apng
import io
from pathlib import Path
import textwrap
from enum import Enum
from typing import Any, Literal, Sequence, get_args
from utilities.misc import cached_get
from utilities.config import get_config
from PIL import Image, ImageDraw, ImageFont
from grapheme import graphemes
from utilities.textbox.characters import Character, Face, get_character

SupportedFacePositions = Literal["left", "center", "right"]
SupportedFiletypes = Literal["WEBP", "GIF", "APNG", "PNG", "JPEG"]


class BackgroundStyle():
	source: str = "OneShot"
	face_position: SupportedFacePositions = "right"
	color: str = "orange"

	def __init__(
	    self,
	    source: str = "OneShot",
	    face_position: SupportedFacePositions = "right",
	    color: str = "orange",
	):
		self.source = source
		self.face_position = face_position
		self.color = color

	def __str__(self):
		sanitized_source = self.source.replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\s')
		return f"{sanitized_source}-{self.face_position}-{self.color}"

	@classmethod
	def from_string(cls, style_string: str):
		try:
			split = style_string.split('-')
			if len(split) != 3:
				raise ValueError("Expected 3 values divided by dashes")
		except ValueError as e:
			raise ValueError(
			    f"Invalid BackgroundStyle format. Expected 'source-facepos-color', but got '{style_string}'"
			) from e
		sanitized_source_str, face_position_str, color_str = split

		source = sanitized_source_str.replace('\\s', ';').replace('\\n', '\n').replace('\\\\', '\\')

		if face_position_str not in get_args(SupportedFacePositions):
			raise ValueError(
			    f"Face position must be one of {' / '.join(get_args(SupportedFacePositions))}, got '{face_position_str}'"
			)
		face_pos: SupportedFacePositions = face_position_str  # type: ignore

		return cls(source, face_position=face_pos, color=color_str)


class FrameOptions:
	background: BackgroundStyle | None = None
	animated: bool = True
	static_delay_override: int | None  # override for the amount of time you show the frame in the gif
	end_delay: int  # time before the arrow shows up
	end_arrow_bounces: int
	end_arrow_delay: int  # how much a singe frame of the arrow should take

	def __init__(
	    self,
	    background: BackgroundStyle | None = None,
	    animated: bool = True,
	    end_delay: int = 150,
	    end_arrow_bounces: int = 4,
	    end_arrow_delay: int = 150,
	    static_delay_override: int | None = None
	):
		self.background = background or BackgroundStyle()
		self.static_delay_override = static_delay_override
		self.animated = animated

		self.end_delay = end_delay
		self.end_arrow_bounces = end_arrow_bounces
		self.end_arrow_delay = end_arrow_delay

	def __str__(self):
		return f"{self.background},{self.animated},{self.end_delay},{self.end_arrow_bounces},{self.end_arrow_delay},{self.static_delay_override}"

	@classmethod
	def from_string(cls, opts_string: str):
		try:
			split = opts_string.split(',')
			if len(split) != 6:
				raise ValueError("Expected 6 values divided by commas")
		except ValueError as e:
			raise ValueError(
			    f"Invalid FrameOptions format. Expected 'background,animated,end_delay,end_arrow_bounces,end_arrow_delay,static_delay_override', but got '{opts_string}'"
			) from e
		background_raw, animated_raw, end_delay_raw, end_arrow_bounces_raw, end_arrow_delay_raw, static_delay_override_raw = split
		background = BackgroundStyle.from_string(background_raw)
		if animated_raw in ("True", "+", "yes", "1"):
			animated = True
		elif animated_raw in ("False", "-", "no", "0"):
			animated = False
		else:
			raise ValueError(f"Invalid value for 'animated', expected boolean, received '{animated_raw}'")
		end_delay = int(end_delay_raw)
		end_arrow_bounces = int(end_arrow_bounces_raw)
		end_arrow_delay = int(end_arrow_delay_raw)
		static_delay_override = None
		if static_delay_override_raw != "None":
			static_delay_override = int(static_delay_override_raw)
		return cls(
		    background=background,
		    animated=animated,
		    end_delay=end_delay,
		    end_arrow_bounces=end_arrow_bounces,
		    end_arrow_delay=end_arrow_delay,
		    static_delay_override=static_delay_override
		)

	def __repr__(self):
		return f"FrameOptions(style={self.background}, animated={self.animated}, end: delay={self.end_delay} arrow: bounces={self.end_arrow_bounces}, delay={self.end_arrow_delay})"


class Frame:
	text: str | None
	starting_character_id: str | None
	starting_face_name: str | None
	options: FrameOptions

	def __init__(
	    self,
	    text: str | None = None,
	    starting_character_id: str | None = None,
	    starting_face_name: str | None = None,
	    options: FrameOptions | None = None,
	):
		self.text = text
		self.starting_character_id = starting_character_id
		self.starting_face_name = starting_face_name
		self.options = options if options else FrameOptions()

	def __str__(self):
		face = "None"
		if self.starting_character_id:
			face = f"@OneShot/{self.starting_character_id}"
			if self.starting_face_name:
				face += f"/{self.starting_face_name}"
		text = self.text or ""
		sanitized_text = text.replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\s')
		return f"{self.options};{face};{sanitized_text}"

	def __repr__(self):
		text = self.text if self.text is not None else f"\"{self.text}\""
		return f"Frame({text}, starting_character={self.starting_character_id}, starting_face={self.starting_face_name}, {self.options.__repr__()})"

	@classmethod
	def from_string(cls, frame_string: str):
		try:
			split = frame_string.split(';', maxsplit=3)
			if len(split) != 3:
				raise ValueError("Expected 3 values divided by semicolons")
		except ValueError as e:
			raise ValueError(
			    f"Invalid FrameOptions format. Expected 'options;face;text', but got '{frame_string}'"
			) from e
		options_raw, face_raw, sanitized_text = split
		starting_character_id = None
		starting_face_name = None
		if face_raw != "None":
			catalogue, character, face = face_raw.split('/')
			if character and face:
				starting_character_id = character
				starting_face_name = face
		options = FrameOptions.from_string(options_raw)
		text = sanitized_text.replace('\\s', ';').replace('\\n', '\n').replace('\\\\', '\\')
		return cls(
		    options=options,
		    starting_character_id=starting_character_id,
		    starting_face_name=starting_face_name,
		    text=text
		)


async def render_textbox(text: str | None,
                         starting_face: Face | None,
                         animated: bool = True) -> tuple[list[Image.Image], list[int]]:
	background = Image.open(await cached_get(Path("src/data/images/textbox/backgrounds/", "normal.png")))
	if text:
		font = ImageFont.truetype(await cached_get(Path(get_config("textbox.font")), force=True), 20)
	if starting_face:
		icon = await starting_face.get_image(size=96)
		icon = icon.resize((96, 96))

	text_x, text_y = 20, 17

	def draw_frame(img: Image.Image, text: str | None = None) -> Image.Image:
		if text:
			d = ImageDraw.Draw(img)
			y_offset = text_y
			for line in textwrap.wrap(text, width=46):
				d.multiline_text((text_x, y_offset), line, font=font, fill=(255, 255, 255))
				y_offset += 25
		if starting_face:
			img.paste(icon, (496, 16), icon.convert('RGBA'))
		return img

	if not animated and (text or starting_face):
		return ([draw_frame(background.copy(), text)], [0])
	if not starting_face and not text:
		return ([draw_frame(background.copy())], [100])

	images: list[Image.Image] = []
	durations: Sequence[int] = []

	if animated and text:
		cumulative_text = ""
		for cluster in graphemes(text):
			duration = 20
			match cluster:
				case '\n':
					duration = 800
				case '.' | '!' | '?' | '．' | '？' | '！':
					duration = 200
				case ',' | '，':
					duration = 40

			cumulative_text += cluster or ""
			images.append(draw_frame(background.copy(), cumulative_text))
			durations.append(duration)
	else:
		images.append(draw_frame(background.copy(), text))
		durations.append(1000)

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
		char = None
		face = None
		if frame.starting_character_id:
			char = get_character(frame.starting_character_id)
		if char and frame.starting_face_name:
			face = char.get_face(frame.starting_face_name)

		image = (await render_textbox(frame.text, face, False))[0][0]
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
		char = None
		face = None
		if frame.starting_character_id:
			char = get_character(frame.starting_character_id)
		if char and frame.starting_face_name:
			face = char.get_face(frame.starting_face_name)

		images, durations = await render_textbox(frame.text, face, frame.options.animated)
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
