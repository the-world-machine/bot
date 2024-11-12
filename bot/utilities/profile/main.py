import io
import json
import textwrap
import aiofiles
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from interactions import File, User
from utilities.emojis import emojis
from utilities.misc import get_image
from utilities.shop.fetch_items import fetch_background, fetch_badge
from utilities.localization import Localization, fnum

import database as db

icons = []
shop_icons = []

wool_icon = None
sun_icon = None
badges = {}

async def load_badges():
    global wool_icon
    global sun_icon
    global badges
    global icons

    icons = []
    
    badges = await fetch_badge()

    for _, badge in badges.items():
        img = await get_image(f'https://cdn.discordapp.com/emojis/{badge["emoji"]}.png?size=128&quality=lossless') # TODO: move to emojis.py
        img = img.convert('RGBA')
        img = img.resize((35, 35), Image.NEAREST)
        icons.append(img)

    wool_icon = await get_image('https://i.postimg.cc/zXnhRLQb/1044668364422918176.png')
    sun_icon = await get_image('https://i.postimg.cc/J49XsNKW/1026207773559619644.png')

    print('Loaded Badges')

async def draw_profile(user: User, filename: str, description: str, locale: str = "en-#") -> io.BytesIO:
    if wool_icon is None:
        await load_badges()

    user_id = user.id
    user_pfp = user.display_avatar.url

    user_data: db.UserData = await db.UserData(user_id).fetch()

    backgrounds = await fetch_background()
    image = await get_image(backgrounds[user_data.equipped_bg]['image'])

    fnt = ImageFont.truetype("bot/font/TerminusTTF-Bold.ttf", 25)  # Font
    title_fnt = ImageFont.truetype("bot/font/TerminusTTF-Bold.ttf", 25)  # Font

    base_profile = ImageDraw.Draw(image, "RGBA")

    base_profile.text((42, 32), Localization.sl("profile.view.image.title", locale, username=user.username), font=title_fnt, fill=(252, 186, 86), stroke_width=2, stroke_fill=(0, 0, 0))

    base_profile.text((210, 140), f"{textwrap.fill(user_data.profile_description, 35)}", font=fnt, fill=(255, 255, 255), stroke_width=2, stroke_fill=0x000000, align='center')

    pfp = await get_image(user_pfp)

    pfp = pfp.resize((148, 148))

    image.paste(pfp, (42, 80), pfp.convert('RGBA'))

    init_x = 60  # Start with the first column (adjust as needed)
    init_y = 310  # Start with the first row (adjust as needed)

    x = init_x # x position of Stamp
    y = init_y # y position of Stamp

    x_increment = 45 # How much to move to the next column
    y_increment = 50 # How much to move down to the next row

    current_row = 0 # Keep track of the current row
    current_column = 1 # Keep track of the current column
    
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

    wool = user_data.wool
    sun = user_data.suns
    base_profile.text((648, 70), f'{fnum(wool)} x', font=fnt, fill=(255, 255, 255), anchor='rt', align='right', stroke_width=2,
           stroke_fill=0x000000)
    image.paste(wool_icon, (659, 63), wool_icon.convert('RGBA'))

    base_profile.text((648, 32), f'{fnum(sun)} x', font=fnt, fill=(255, 255, 255), anchor='rt', align='right', stroke_width=2,
           stroke_fill=0x000000)
    image.paste(sun_icon, (659, 25), sun_icon.convert('RGBA'))

    base_profile.text((42, 251), Localization.sl("profile.view.image.unlocked.stamps", locale, username=user.username), font=fnt, fill=(255, 255, 255), stroke_width=2, stroke_fill=0x000000)

    img_buffer = io.BytesIO()
    image.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return File(file=img_buffer, file_name=f"{filename}.png", description=description)