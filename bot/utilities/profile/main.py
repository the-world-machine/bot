import io
import textwrap
from termcolor import colored
from interactions import File, User
from utilities.message_decorations import Colors
from utilities.database.schemas import UserData
from utilities.misc import cached_get, pretty_user
from utilities.config import debugging, get_config
from utilities.localization import Localization, fnum
from utilities.shop.fetch_items import fetch_background, fetch_badge
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageSequence

icons = []
shop_icons = []

wool_icon = None
sun_icon = None
badges = {}
font = None


async def load_profile_assets():
	global wool_icon
	global sun_icon
	global badges
	global icons
	global font
	if debugging():
		print("Loading profile assets")
	else:
		print("Loading profile assets ... \033[s", flush=True)

	icons = []
	assets = 0
	try:
		font = ImageFont.truetype(get_config("textbox.font"), 25)
		if debugging():
			print(f"| Font: {font.getname()}")

		assets += 1
	except Exception as e:
		print(colored("Failed to load textbox font", "red"))
		raise e
	badges = await fetch_badge()

	for _, badge in badges.items():
		badge
		img = Image.open(
		    await cached_get(f'https://cdn.discordapp.com/emojis/{badge["emoji"]}.png?size=128&quality=lossless')
		)
		img = img.convert('RGBA')
		img = img.resize((35, 35), Image.NEAREST)
		if debugging():
			print("| Badge id:", badge["id"])
		icons.append(img)
		assets += 1

	wool_icon = await cached_get('https://i.postimg.cc/zXnhRLQb/1044668364422918176.png')
	if debugging():
		print(f"| Wool icon")
	assets += 1
	sun_icon = await cached_get('https://i.postimg.cc/J49XsNKW/1026207773559619644.png')
	if debugging():
		print(f"| Sun icon")
	assets += 1
	if not debugging():
		print(f"\033[udone ({assets})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({assets})")


async def draw_profile(user: User, filename: str, alt: str = None, loc: Localization = Localization()) -> File:
	if wool_icon is None:
		await load_profile_assets()
	user_id = user.id
	user_pfp_url = user.display_avatar._url
	animated = user.display_avatar.animated
	if animated:
		user_pfp_url += ".gif"
	else:
		user_pfp_url += ".png"

	user_pfp_url += "?size=160&quality=lossless"

	user_data: UserData = await UserData(_id=user_id).fetch()

	title = loc.l("profile.view.image.title", username=user.display_name)

	backgrounds = await fetch_background()
	image = await cached_get(backgrounds[user_data.equipped_bg]['image'])

	base_profile = ImageDraw.Draw(image, "RGBA")

	base_profile.text((42, 32), title, font=font, fill=(252, 186, 86), stroke_width=2, stroke_fill=(0, 0, 0))
	if len(user_data.profile_description) > 0:
		# textwrap.fill makes it so the text doesn't overflow out of the image
		base_profile.text(
		    (210, 140),
		    textwrap.fill(user_data.profile_description, 35),
		    font=font,
		    fill=(255, 255, 255),
		    stroke_width=2,
		    stroke_fill=Colors.BLACK.hex,
		    align='center'
		)

	init_x = 60  # Start with the first column (adjust as needed)
	init_y = 310  # Start with the first row (adjust as needed)

	x = init_x  # x position of Stamp
	y = init_y  # y position of Stamp

	x_increment = 45  # How much to move to the next column
	y_increment = 50  # How much to move down to the next row

	current_row = 0  # Keep track of the current row
	current_column = 1  # Keep track of the current column

	badge_keys = list(badges.keys())

	for i, icon in enumerate(icons):

		enhancer = ImageEnhance.Brightness(icon)

		icon = enhancer.enhance(0)

		if badge_keys[i] in user_data.owned_badges:
			icon = enhancer.enhance(1)

		image.paste(icon, (x, y), icon)

		x += x_increment  # Move to the next column

		# If we have reached the end of a row
		if (i + 1) % 5 == 0:
			x = init_x  # Reset to the first column
			y += y_increment  # Move to the next row
			current_row += 1

		# If we have displayed all the rows, start the next one.
		if current_row == 3:
			init_x = (init_x + x_increment * 5) * current_column + 10

			x = init_x
			y = init_y

			current_column += 1
			current_row = 0

	base_profile.text(
	    (648, 70),
	    f'{fnum(user_data.wool, locale=loc.locale)} x',
	    font=font,
	    fill=(255, 255, 255),
	    anchor='rt',
	    align='right',
	    stroke_width=2,
	    stroke_fill=Colors.BLACK.hex
	)
	image.paste(wool_icon, (659, 63), wool_icon.convert('RGBA'))

	base_profile.text(
	    (648, 32),
	    f'{fnum(user_data.suns, locale=loc.locale)} x',
	    font=font,
	    fill=(255, 255, 255),
	    anchor='rt',
	    align='right',
	    stroke_width=2,
	    stroke_fill=Colors.BLACK.hex
	)
	image.paste(sun_icon, (659, 25), sun_icon.convert('RGBA'))

	base_profile.text(
	    (42, 251),
	    loc.l("profile.view.image.unlocked.stamps", username=user.username),
	    font=font,
	    fill=(255, 255, 255),
	    stroke_width=2,
	    stroke_fill=Colors.BLACK.hex
	)

	pfp = await cached_get(user_pfp_url)
	frames = []
	if animated:
		for pfp_frame in ImageSequence.Iterator(pfp):
			temp_image = image.copy()
			pfp_frame = pfp_frame.resize((148, 148))
			temp_image.paste(pfp_frame, (42, 80), pfp_frame.convert('RGBA'))
			frames.append(temp_image)
	else:
		pfp = pfp.resize((148, 148))
		image.paste(pfp, (42, 80), pfp.convert('RGBA'))
		frames.append(image)

	img_buffer = io.BytesIO()
	if animated:
		frames[0].save(img_buffer, format="GIF", save_all=True, append_images=frames[1:], loop=0, duration=100)
	else:
		image.save(img_buffer, format="PNG")
	img_buffer.seek(0)

	# TODO: move this out of here sometime
	username = pretty_user(user)

	alt = alt if alt is not None else loc.l(
	    "profile.view.image.alt_nodescription",
	    username=username,
	    suns=user_data.suns,
	    wool=user_data.wool,
	)
	if len(user_data.profile_description) > 0:
		alt = loc.l(
		    "profile.view.image.alt_cont",
		    alt_nodescription=alt,
		    description=user_data.profile_description,
		    username=username,
		    suns=user_data.suns,
		    wool=user_data.wool,
		)
	return File(file=img_buffer, file_name=filename + (".gif" if animated else ".png"), description=alt)