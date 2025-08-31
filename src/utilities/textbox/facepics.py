import io
import os
from pathlib import Path
import re
from PIL import Image
from interactions import PartialEmoji
import yaml
from termcolor import colored
from datetime import datetime
from extensions.events.Ready import ReadyEvent
from utilities.config import debugging, get_config
from utilities.emojis import make_emoji_cdn_url
from utilities.misc import cached_get, is_domain_allowed

facepics: dict = {}
last_update: datetime | None = None

icon_regex = re.compile(r"^\d+$")


class Face:
	path: str
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
		    _custom else await cached_get(loc if loc else make_emoji_cdn_url(emoji_id=self.icon, size=size))
		)

	def __init__(self, path: str, icon: str | None = None):
		self.path = path
		if icon and not icon_regex.match(icon):
			raise ValueError(f"Invalid icon, got {icon}")
		self.icon = icon

	def __repr__(self):
		return f"Face({self.icon})"


def parse_recursive(data: dict) -> dict:
	output = {}

	sub_content = data.get("faces", data.get("characters", data))

	for key, value in sub_content.items():
		if key in [ "icon", "faces", "characters"]:
			continue

		if isinstance(value, dict):
			node = parse_recursive(value)
			if "icon" in value:
				node["__icon"] = value.get("icon")
			output[key] = node
		else:
			output[key] = value

	return output


def load_facepics():
	with open('src/data/facepics.yml', 'r') as f:
		data = yaml.safe_load(f)

	loaded_chars = {}
	for top_key, top_value in data.items():
		node = parse_recursive(top_value)
		if "icon" in top_value:
			node["__icon"] = top_value.get("icon")
		loaded_chars[top_key] = node

	return loaded_chars


def on_file_update(filename):
	global facepics, last_update

	current_time = datetime.now()
	debounce_interval = 1

	if last_update and (current_time - last_update).seconds < debounce_interval:
		return print(".", end="")

	last_update = current_time
	print(colored('─ Reloading facepics ...', 'yellow'), end="")

	try:
		facepics = load_facepics()
	except Exception as e:
		print(colored(" FAILED", "red"))
		ReadyEvent.log("## Failed to reload facepics\n" + str(e))
		return

	print(" ─ ─ ─ ")


async def get_facepic(path: str) -> Face | None:
	face = Face(path)
	if path.startswith("https://"):
		if is_domain_allowed(path, allowed_domains=get_config('textbox.allowed-hosts', typecheck=list)):
			await face.set_custom_icon(path)
		else:
			face.path = "Other/NAVI"
		return face
	else:
		parts = path.split('/')
		at = facepics
		try:
			for part in parts:
				at = at[part]

			if isinstance(at, str) or at is None:
				return Face(path, icon=at)
			else:
				print(f"Couldn't find face for path {path}")
				return await get_facepic("Other/NAVI")
		except (KeyError, TypeError) as e:
			print(e)
			return await get_facepic("Other/NAVI")


if debugging():
	print("Loading facepics")
else:
	print("Loading facepics ... \033[s", flush=True)

facepics = load_facepics()
character_count = sum(len(v.keys()) for v in facepics.values() if isinstance(v, dict) and "__icon" not in v)

if not debugging():
	print(f"\033[udone ({character_count})", flush=True)
	print("\033[999B", end="", flush=True)
else:
	print(f"Done ({character_count})")
