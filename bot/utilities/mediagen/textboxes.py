import apng
import io
from pathlib import Path
import textwrap
from enum import Enum
from typing import Literal
from utilities.misc import cached_get
from utilities.config import get_config
from PIL import Image, ImageDraw, ImageFont
from grapheme import graphemes
from utilities.textbox.characters import Character, Face, get_character


class Styles(Enum):
	NORMAL_LEFT: int = 0
	NORMAL_RIGHT: int = 1


SupportedFiletypes = Literal["WEBP", "GIF", "APNG", "PNG", "JPEG"]


class FrameOptions:
	style: Styles = Styles.NORMAL_RIGHT
	animated: bool = True

	end_delay: int
	end_arrow_bounces: int
	end_arrow_delay: int

	def __init__(
	    self,
	    style: Styles = Styles.NORMAL_RIGHT,
	    animated: bool = True,
	    end_delay: int = 150,
	    end_arrow_bounces: int = 3,
	    end_arrow_delay: int = 150
	):
		self.style = style
		self.animated = animated

		self.end_delay = end_delay
		self.end_arrow_bounces = end_arrow_bounces
		self.end_arrow_delay = end_arrow_delay


class Frame:
	text: str | None
	starting_character_id: Character | None
	starting_face_name: Face | None
	options: FrameOptions

	def __init__(
	    self,
	    text: str | None = None,
	    starting_character_id: str | None = None,
	    starting_face_name: str | None = None,
	    options: FrameOptions = None,
	):
		self.text = text
		self.starting_character_id = starting_character_id
		self.starting_face_name = starting_face_name
		self.options = options if options else FrameOptions()

	def __repr__(self):
		return f"Frame(\"{self.text}\", starting_character={self.starting_character_id}, starting_face={self.starting_face_name}, options)"


async def render_textbox(text: str | None,
                         starting_face: Face | None,
                         animated: bool = True) -> tuple[list[Image.Image], list[float]] | Image.Image:
	background = Image.open(await cached_get(Path("bot/data/images/textbox/backgrounds/", "normal.png")))
	if text:
		font = ImageFont.truetype(await cached_get(Path(get_config("textbox.font")), force=True), 20)
	if starting_face:
		icon = await starting_face.get_image(size=96)
		icon = icon.resize((96, 96))

	text_x, text_y = 20, 17

	def draw_frame(img: Image.Image = None, text: str = None) -> Image.Image:
		if text:
			d = ImageDraw.Draw(img)
			y_offset = text_y
			for line in textwrap.wrap(text, width=46):
				d.text((text_x, y_offset), line, font=font, fill=(255, 255, 255))
				y_offset += 25
		if starting_face:
			img.paste(icon, (496, 16), icon.convert('RGBA'))
		return img

	if not animated and (text or starting_face):
		return [draw_frame(background.copy(), text), [0]]
	if not starting_face and not text:
		return [draw_frame(background.copy()), [100]]

	images: list[Image.Image] = []
	durations: list[int] = []

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

			cumulative_text += cluster
			images.append(draw_frame(background.copy(), cumulative_text))
			durations.append(duration)
	else:
		images.append(draw_frame(background.copy(), text))
		durations.append(1000)

	return images, durations


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
    frames: dict[str, Frame],
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
		frame = frames[frame_index]
		char = None
		face = None
		if frame.starting_character_id:
			char = get_character(frame.starting_character_id)
		if char and frame.starting_face_name:
			face = char.get_face(frame.starting_face_name)

		image = (await render_textbox(frame.text, face, False))[0]
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
			    buffer, format="PNG", compress_level=9 - int(max(0, min(100, quality)) * 9 / 100)
			)  #  quality = 0->100 = compress_level = 9->0
		return buffer

	for frame in frames.values():
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
		arrow = Image.open(await cached_get(Path("bot/data/images/textbox/backgrounds/", "normal_arrow.png")))
		arrow_rgba = arrow.convert('RGBA')
		last_frame = all_images[-1]
		all_durations[-1] = 1500
		bounce_frames = [
		    ":3",
		    last_frame.copy(),
		    last_frame.copy(),
		    last_frame.copy(),
		]
		bounce_frames[1].paste(arrow, (299, 119), arrow_rgba)
		bounce_frames[2].paste(arrow, (299, 119 - 1), arrow_rgba)
		bounce_frames[3].paste(arrow, (299, 119 - 2), arrow_rgba)

		for i in bounce(4, 3):
			all_images.append(bounce_frames[i])
			all_durations.append(150)
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
				png_images.append(temp_buffer.getvalue())

			animation = apng.APNG()
			for i, png_data in enumerate(png_images):
				animation.append(png_data, delay=all_durations[i] / 1000)  # APNG uses seconds instead of ms

			animation.save(buffer)
		case "GIF":
			all_images[0].save(
			    buffer,
			    format="GIF",
			    save_all=True,
			    append_images=all_images[1:],
			    duration=all_durations,
			)
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
