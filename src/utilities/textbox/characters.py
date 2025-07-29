import io
import os
import yaml
import re
from datetime import datetime
from PIL import Image
from pathlib import Path
from termcolor import colored
from utilities.emojis import make_url
from utilities.misc import cached_get
from interactions import PartialEmoji
from utilities.config import debugging
from extensions.events.Ready import ReadyEvent

icon_regex = re.compile(r"^\d+$")


class Face:
	icon: str | None = None
	_custom: io.BytesIO | bytes | None = None

	async def set_custom_icon(self, loc: str | Path):
		self._custom = await cached_get(loc)

	def get_icon_emoji(self) -> PartialEmoji:
		return PartialEmoji(id=int(self.icon)) if self.icon else PartialEmoji(name="❔")

	async def get_image(self, size: int | None) -> Image.Image:
		loc: str | None = f"src/data/images/textbox/{self.icon}.png"
		if not os.path.exists(loc):
			loc = None
		return Image.open(
		    self._custom if self.
		    _custom else await cached_get(loc if loc else make_url(f"<:i:{self.icon}>", size=size))
		)

	def __init__(self, icon: str | None = None):
		if icon and not icon_regex.match(icon):
			raise ValueError(f"Invalid icon, got {icon}")
		self.icon = icon

	def __repr__(self):
		return f"Face({self.icon})"


class Character:
	faces: dict[str, Face]
	icon: str | None

	def get_face(self, name):
		if name not in self.faces:
			raise ValueError(f'Face "{name}" not found')
		return self.faces[name]

	def get_faces(self) -> list[tuple[str, Face]]:
		return list(self.faces.items())

	def get_face_list(self) -> list[str]:
		return list(self.faces.keys())

	def has_face(self, name):
		return hasattr(self.faces, name)

	def get_icon_emoji(self) -> PartialEmoji:
		return (PartialEmoji(id=self.icon) if self.icon else self.faces["Normal"].get_icon_emoji())

	def __init__(self, faces: dict[str, str], icon: str | None = None):
		if icon and not icon_regex.match(icon):
			raise ValueError(f"Invalid icon, got {icon}")
		self.icon = icon

		self.faces = {}
		for name, ic in faces.items():
			self.faces[name] = Face(ic)

	def __repr__(self):
		facecount = len(self.faces)
		return f'Character({f"icon={self.icon}," if self.icon else ""}{facecount} face{"" if facecount == 0 else "s"})'


env = {
    "characters": {},
    "last_update": None,
}


def load_characters():
	with open('src/data/characters.yml', 'r') as f:
		return yaml.safe_load(f)


def get_character(id: str) -> Character:
	if id not in env["characters"]:
		raise ValueError(f'Character "{id}" not found')
	return env["characters"][id]


def get_characters() -> list[tuple[str, Character]]:
	return env["characters"].items()


def get_character_list() -> list[str]:
	return env["characters"].keys()


def parse(input: dict):
	chars = {}
	for name, char in input.items():
		chars[name] = Character(icon=char["icon"] if "icon" in char else None, faces=char["faces"])

	return chars


if debugging():
	print("Loading characters")
else:
	print("Loading characters ... \033[s", flush=True)

env["characters"] = parse(load_characters())

if not debugging():
	print(f"\033[udone ({len(env['characters'].keys())})", flush=True)
	print("\033[999B", end="", flush=True)
else:
	print(f"Done ({len(env['characters'].keys())})")

debounce_interval = 1  # seconds


def on_file_update(filename):
	current_time = datetime.now()
	if filename in env["last_update"] and (current_time - env["last_update"]).seconds < debounce_interval:
		return print(".", end="")
	env["last_update"] = current_time
	print(colored(f'─ Reloading characters ...', 'yellow'), end="")
	try:
		env["characters"] = parse(load_characters())
	except Exception as e:
		print(colored(" FAILED", "red"))
		ReadyEvent.log("## Failed to reload characters\n" + str(e))
		return
	print(" ─ ─ ─ ")
