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

from utilities.textbox.characters import Character, Face


class Styles(Enum):
	NORMAL_LEFT: int = 0
	NORMAL_RIGHT: int = 1


class Frame:
	style: Styles = Styles.NORMAL_RIGHT

	animated: bool = False
	text: str | None
	character_id: Character | None
	face_name: Face | None

	def check(self):
		return self.character_id is not None and self.face_name is not None

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


async def render_frame(text: str | None, face: Face | None, animated: bool = False) -> io.BytesIO:
	background = Image.open(await cached_get(Path("bot/data/images/textbox/backgrounds/", "normal.png")))
	if text:
		font = ImageFont.truetype(await cached_get(Path(get_config("textbox.font")), force=True), 20)
	if face:
		icon = await face.get_image(size=96)
		icon = icon.resize((96, 96))

	text_x, text_y = 20, 17
	img_buffer = io.BytesIO()
	frames: list[Image.Image] = []

	def draw_frame(img, text):
		if text:
			d = ImageDraw.Draw(img)
			y_offset = text_y
			for line in textwrap.wrap(text, width=46):
				d.text((text_x, y_offset), line, font=font, fill=(255, 255, 255))
				y_offset += 25
		if face:
			img.paste(icon, (496, 16), icon.convert('RGBA'))
		return img

	if text and animated:
		cumulative_text = ""
		for char in text:
			cumulative_text += char
			frame_img = draw_frame(background.copy(), cumulative_text)
			match char:
				case '.' | '!' | '?':
					frame_delay = 10
				case ',':
					frame_delay = 4
				case _:
					frame_delay = 1

			frames.extend([frame_img] * frame_delay)

		frames[0].save(img_buffer, format="GIF", save_all=True, append_images=frames, duration=40)
	else:
		final_frame = draw_frame(background, text)
		final_frame.save(img_buffer, format="PNG")

	img_buffer.seek(0)
	return img_buffer


async def make_textboxes(*frames: dict[str, Frame]):
	pass
