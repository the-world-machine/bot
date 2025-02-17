import io
from pathlib import Path
import textwrap
from enum import Enum
from datetime import datetime
from interactions import File
from utilities.misc import cached_get
from utilities.config import get_config
from PIL import Image, ImageDraw, ImageFont

from utilities.textbox.characters import Face

class Styles(Enum):
	NORMAL_LEFT: int = 0
	NORMAL_RIGHT: int = 1

async def render_textbox(
    text: str,
    face: Face,
    animated: bool = False,
    filename: str = f"{datetime.now()}-textbox",
    alt_text: str = None
) -> File:
	img = Image.open(await cached_get(Path("bot/data/images/textbox/backgrounds/", "normal.png")))
	icon = await face.get_image(size=96)
	icon = icon.resize((96, 96))

	fnt = ImageFont.truetype(await cached_get(Path(get_config("textbox.font")), force=True), 20)
	text_x, text_y = 20, 17
	img_buffer = io.BytesIO()
	frames = []

	def draw_frame(img, text_content):
		d = ImageDraw.Draw(img)
		y_offset = text_y
		for line in textwrap.wrap(text_content, width=46):
			d.text((text_x, y_offset), line, font=fnt, fill=(255, 255, 255))
			y_offset += 25
		img.paste(icon, (496, 16), icon.convert('RGBA'))
		return img

	if animated:
		cumulative_text = ""
		for char in text:
			cumulative_text += char
			frame_img = draw_frame(img.copy(), cumulative_text)
			match char:
				case '.' | '!' | '?':
					frame_delay = 10
				case ',':
					frame_delay = 4
				case _:
					frame_delay = 1

			frames.extend([frame_img] * frame_delay)

		frames[0].save(img_buffer, format="GIF", save_all=True, append_images=frames, duration=40)
		filename = f"{filename}.gif"
	else:
		final_frame = draw_frame(img, text)
		final_frame.save(img_buffer, format="PNG")
		filename = f"{filename}.png"

	img_buffer.seek(0)
	return File(file=img_buffer, file_name=filename, description=alt_text if alt_text else text)
