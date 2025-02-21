import builtins
import io
from pathlib import Path
import textwrap
from enum import Enum
from datetime import datetime
from typing import Literal
from interactions import File
from utilities.misc import cached_get
from utilities.config import get_config
from PIL import Image, ImageDraw, ImageFont

from utilities.textbox.characters import Character, Face, get_character


class Styles(Enum):
	NORMAL_LEFT: int = 0
	NORMAL_RIGHT: int = 1


class Frame:
	style: Styles = Styles.NORMAL_RIGHT

	animated: bool = False
	text: str | None
	character_id: Character | None
	face_name: Face | None

	def __init__(
	    self,
	    style: Literal[0, 1] = 1,
	    animated: bool = False,
	    text: str | None = None,
	    character_id: str | None = None,
	    face_name: str | None = None
	):
		self.style = style
		self.text = text
		self.animated = animated
		self.character_id = character_id
		self.face_name = face_name

	def __repr__(self):
		return f"Frame(character={self.character_id}, face={self.face_name})"


PALCEHOLDER_DELAY_BETWEEN_CHARACTERS_Bleh = 2000  # this needs to go to the end of the last frame


async def render_frame(text: str | None,
                       face: Face | None,
                       animated: bool = True) -> tuple[list[Image.Image], list[float]] | Image.Image:
	background = Image.open(await cached_get(Path("bot/data/images/textbox/backgrounds/", "normal.png")))
	if text:
		font = ImageFont.truetype(await cached_get(Path(get_config("textbox.font")), force=True), 20)
	if face:
		icon = await face.get_image(size=96)
		icon = icon.resize((96, 96))

	text_x, text_y = 20, 17

	def draw_frame(img: Image.Image = None, text: str = None) -> Image.Image:
		if text:
			d = ImageDraw.Draw(img)
			y_offset = text_y
			for line in textwrap.wrap(text, width=46):
				d.text((text_x, y_offset), line, font=font, fill=(255, 255, 255))
				y_offset += 25
		if face:
			img.paste(icon, (496, 16), icon.convert('RGBA'))
		return img

	if not animated and (text or face):
		return [draw_frame(background.copy(), text)]
	if not face and not text:
		return [draw_frame(background.copy())]

	images: list[Image.Image] = []
	if animated:
		if face and not text:
			return [draw_frame(background.copy())]

		cumulative_text = ""
		for char in text:
			cumulative_text += char
			duration = 1
			match char:
				case '.' | '!' | '?' | '．' | '？' | '！':
					duration = 200
				case ',' | '，':
					duration = 40

			images.extend(draw_frame(background.copy(), cumulative_text) * duration)

	return images


async def make_textboxes(frames: dict[str, Frame]):
	frame_images: list[Image.Image] = []
	for frame in frames.values():
		char = None
		face = None
		if frame.character_id:
			char = get_character(frame.character_id)
		if char and frame.face_name:
			face = char.get_face(frame.face_name)

		images, durs = await render_frame(frame.text, face)
		frame_images.extend(images)
	buffer = io.BytesIO()
	frame_images[0].save(buffer, format="GIF", save_all=True, append_images=frame_images[1:], loop=0)
	return buffer
