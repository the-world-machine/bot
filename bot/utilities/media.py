import io
import textwrap
from datetime import datetime
from interactions import File
from utilities.misc import get_image
from utilities.config import get_config
from PIL import Image, ImageDraw, ImageFont


async def generate_dialogue(text, icon_url, animated=False, filename=f"{datetime.now()}-textbox") -> File:
	img = Image.open("bot/data/images/textbox/niko-background.png")
	icon = await get_image(url=icon_url)
	icon = icon.resize((96, 96))

	fnt = ImageFont.truetype(get_config("textbox.font"), 20)
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
	return File(file=img_buffer, file_name=filename, description=text)
