from datetime import datetime
import io
from interactions import *
import json
from uuid import uuid4
import os

import yaml
from data.emojis import emojis
from data.localization import Localization
from utilities.message_decorations import fancy_message, fancy_embed
from PIL import Image, ImageDraw, ImageFont
import textwrap
import aiohttp
import aiofiles

class Face:
    def __init__(self, name: str, emoji: int):
        self.name = name
        self.emoji = emoji

    def __repr__(self):
        return f"Face(name={self.name}, emoji={self.emoji})"

class Character:
    def __init__(self, name: str, faces: list[Face]):
        self.name = name
        self.faces = faces

    def __repr__(self):
        return f"Character(name={self.name}, faces={self.faces})"

_yac: dict[str, Image.Image] = {}

async def get_Image(url: str) -> Image.Image:
    if url in _yac:
        return _yac[url]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                file = io.BytesIO(await resp.read())

                _yac[url] = file
                return Image.open(_yac[url])
            else:
                raise ValueError(f"{resp.status} Discord cdn shittig!!")
            
class TextboxModule(Extension):
    _characters = None
    _last_modified = None

    @staticmethod
    def get_characters() -> list[Character]:
        path = 'bot/data/characters.yml'
        
        if TextboxModule._characters is None or (os.path.getmtime(path) != TextboxModule._last_modified):
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                TextboxModule._characters = [
                    Character(
                        name=character['name'],
                        faces=[
                            Face(name=face['name'], emoji=face['emoji']) for face in character['faces']
                        ]
                    )
                    for character in data['characters']
                ]
                TextboxModule._last_modified = os.path.getmtime(path)

        return TextboxModule._characters

    @staticmethod
    async def generate_welcome_message(guild: Guild, user: Member, message: str):

        uuid = str(uuid4())

        message = message.replace('[user]', user.username)
        message = message.replace('[server]', guild.name)

        image = await TextboxModule.generate_dialogue(message,
                                                  'https://cdn.discordapp.com/emojis/1023573458296246333.webp?size=128&quality=lossless',
                                                  uuid)

        file = File(file=image, description=message)
        await guild.system_channel.send(user.mention, files=file)

    @staticmethod
    async def generate_dialogue(text, icon_url, animated=False, filename=f"{datetime.now()}-textbox"):
        img = Image.open("bot/images/textbox/niko-background.png")
        icon = await get_Image(url=icon_url)
        icon = icon.resize((96, 96))
        
        fnt = ImageFont.truetype("bot/font/TerminusTTF-Bold.ttf", 20)
        text_x, text_y = 20, 17
        img_buffer = io.BytesIO()
        frames = []  # Using ImageSequence-compatible frames list
        
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
                
            frames[0].save(
                img_buffer, format="GIF", save_all=True, append_images=frames, duration=40
            )
            filename = f"{filename}.gif"
        else:
            final_frame = draw_frame(img, text)
            final_frame.save(img_buffer, format="PNG")
            filename = f"{filename}.png"
            
        img_buffer.seek(0)
        return File(file=img_buffer, file_name=filename, description=text)
    
    @staticmethod        
    def make_characters_select_menu(locale: Localization, characters: list[Character] = None):
        if characters is None:
            characters = TextboxModule.get_characters()
        options = []

        for character in characters:
            name = character.name

            options.append(
                StringSelectOption(
                    label=name,
                    emoji=PartialEmoji(id=character.faces[0].emoji),
                    value=name
                )
            )

        return StringSelectMenu(
            *options,
            placeholder="Select a character!",
            custom_id="textbox_select_char"
        )
    
    @staticmethod
    def make_faces_select_menu(locale: Localization, character_name: str, characters: list[Character] = None):
        if characters is None:
            characters = TextboxModule.get_characters()

        options = []

        character = next((char for char in characters if char.name == character_name), None)
        if character is None:
            raise ValueError(f"Character '{character_name}' not found.")

        for face in character.faces:
            emoji = face.emoji if isinstance(face.emoji, str) else PartialEmoji(id=face.emoji)

            options.append(
                StringSelectOption(
                    label=face.name,
                    value=face.emoji,
                    emoji=emoji
                )
            )

        return StringSelectMenu(
            *options,
            custom_id='textbox_select_face',
            disabled=False,
            placeholder='Select a face!'
        )

    @slash_command(description='Generate a OneShot textbox!')
    @slash_option(description='What you want the character to say?', max_length=180, name='text',
                  opt_type=OptionType.STRING, required=True)
    @slash_option(description='Do you want the text to appear slowly? (will take more time)', name='animated',
                  opt_type=OptionType.BOOLEAN, required=True)
    async def textbox(self, ctx: SlashContext, text: str, animated: bool):
        await ctx.defer(ephemeral=True)

        characters_select = self.make_characters_select_menu(ctx.locale)

        await fancy_message(ctx, f"[ <@{ctx.user.id}>, select a character. ]", ephemeral=True, components=characters_select)

        char = await self.bot.wait_for_component(components=characters_select)

        char_ctx = char.ctx

        await char_ctx.defer(edit_origin=True)

        faces_select = self.make_faces_select_menu(ctx.locale, character_name=char_ctx.values[0])

        await ctx.edit(embed=fancy_embed(f"[ <@{ctx.user.id}>, select a face. ]"), components=faces_select)

        char_ctx = await self.bot.wait_for_component(components=faces_select)

        await char_ctx.ctx.defer(edit_origin=True)

        value = char_ctx.ctx.values[0]

        await ctx.edit(embeds=fancy_embed(f"[ Generating Image... {emojis['icon_loading']} ]"))

        if value == '964952736460312576':
            icon = ctx.author.avatar.url
        else:
            icon = f'https://cdn.discordapp.com/emojis/{value}.png'
            
        await ctx.edit(embeds=fancy_embed(f"[ Uploading image... {emojis['icon_loading']} ]"), components=[])
        file = await TextboxModule.generate_dialogue(text, icon, animated)
        await ctx.channel.send(message=f"-# [ by {ctx.user.mention} ]", files=file)
        await ctx.edit(embeds=fancy_embed(f"[ Done! ]"))
