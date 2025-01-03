import os
import yaml
from interactions import *
from utilities.emojis import emojis
from utilities.media import generate_dialogue
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message


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


class TextboxModule(Extension):
	_characters = None
	_last_modified = None

	@staticmethod
	def get_characters() -> list[Character]:
		path = 'bot/data/characters.yml'

		if TextboxModule._characters is None or (
		    os.path.getmtime(path) != TextboxModule._last_modified):
			with open(path, 'r') as f:
				data = yaml.safe_load(f)
				TextboxModule._characters = [
				    Character(name=character['name'],
				              faces=[
				                  Face(name=face['name'], emoji=face['emoji'])
				                  for face in character['faces']
				              ])
				    for character in data['characters']
				]
				TextboxModule._last_modified = os.path.getmtime(path)

		return TextboxModule._characters

	@staticmethod
	def make_characters_select_menu(locale: Localization,
	                                characters: list[Character] = None):
		if characters is None:
			characters = TextboxModule.get_characters()
		options = []

		for character in characters:
			name = character.name

			options.append(
			    StringSelectOption(
			        label=name,
			        emoji=PartialEmoji(id=character.faces[0].emoji),
			        value=name))

		return StringSelectMenu(*options,
		                        placeholder="Select a character!",
		                        custom_id="textbox_select_char")

	@staticmethod
	def make_faces_select_menu(locale: Localization,
	                           character_name: str,
	                           characters: list[Character] = None):
		if characters is None:
			characters = TextboxModule.get_characters()

		options = []

		character = next(
		    (char for char in characters if char.name == character_name), None)
		if character is None:
			raise ValueError(f"Character '{character_name}' not found.")

		for face in character.faces:
			emoji = face.emoji if isinstance(face.emoji, str) else PartialEmoji(
			    id=face.emoji)

			options.append(
			    StringSelectOption(label=face.name,
			                       value=face.emoji,
			                       emoji=emoji))

		return StringSelectMenu(*options,
		                        custom_id='textbox_select_face',
		                        disabled=False,
		                        placeholder='Select a face!')

	@slash_command(description='Generate a OneShot textbox!')
	@slash_option(description='What you want the character to say?',
	              max_length=180,
	              name='text',
	              opt_type=OptionType.STRING,
	              required=True)
	@slash_option(
	    description=
	    'Do you want the text to appear slowly? (will take more time)',
	    name='animated',
	    opt_type=OptionType.BOOLEAN,
	    required=True)
	async def textbox(self, ctx: SlashContext, text: str, animated: bool):
		await ctx.defer(ephemeral=True)

		characters_select = self.make_characters_select_menu(ctx.locale)

		await fancy_message(ctx,
		                    f"[ <@{ctx.user.id}>, select a character. ]",
		                    ephemeral=True,
		                    components=characters_select)
		char = await ctx.client.wait_for_component(components=characters_select)
		ctx = char.ctx
		await ctx.defer(edit_origin=True)

		char = await ctx.client.wait_for_component(components=characters_select)
		ctx = char.ctx
		await ctx.defer(edit_origin=True)
		faces_select = self.make_faces_select_menu(ctx.locale,
		                                           character_name=ctx.values[0])

		await ctx.edit(embed=Embed(
		    description=f"[ <@{ctx.user.id}>, select a face. ]",
		    color=Colors.DARKER_WHITE),
		               components=faces_select)
		faces = await ctx.client.wait_for_component(components=faces_select)
		ctx = faces.ctx
		await ctx.defer(edit_origin=True)
		value = ctx.values[0]

		await ctx.edit(embed=Embed(
		    description=f"[ Generating Image... {emojis['icons']['loading']} ]",
		    color=Colors.DARKER_WHITE))

		if value == '964952736460312576':
			icon = ctx.author.avatar.url
		else:
			icon = f'https://cdn.discordapp.com/emojis/{value}.png'

		await ctx.edit(embed=Embed(
		    description=f"[ Uploading image... {emojis['icons']['loading']} ]",
		    color=Colors.DARKER_WHITE),
		               components=[])
		file = await generate_dialogue(text, icon, animated)
		await ctx.channel.send(content=f"-# [ {ctx.user.mention} ]",
		                       files=file,
		                       allowed_mentions={'users': []})
		await ctx.edit(embed=Embed(description=f"[ Done! ]",
		                           color=Colors.DARKER_WHITE),
		               components=[])
