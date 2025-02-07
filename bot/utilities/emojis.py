import re
from typing import Literal, TypedDict
from yaml import safe_load
from termcolor import colored
from utilities.data_watcher import subscribe


def flatten_emojis(data: dict, parent_key: str = ''):
	items = []
	for k, v in data.items():
		key = f"{parent_key}.{k}" if parent_key else k
		if isinstance(v, dict):
			items.extend(flatten_emojis(v, key).items())
		else:
			items.append((key, v))
	return dict(items)


def unflatten_emojis(flat_data: dict) -> dict:
	unflattened = {}
	for flat_key, value in flat_data.items():
		keys = flat_key.split(".")
		d = unflattened
		for key in keys[:-1]:
			d = d.setdefault(key, {})
		d[keys[-1]] = value
	return unflattened


def minify_emoji_names(data):
	if isinstance(data, dict):
		return { key: minify_emoji_names(value) for key, value in data.items() }
	elif isinstance(data, str):
		# replaces all names with "i" for more embed space
		return re.sub(r'(?<=[:])\w+(?=:\d)', 'i', data)
	return data


class ProgressBar(TypedDict):
	empty: dict[Literal["start", "middle", "end"], str]
	filled: dict[Literal["start", "middle", "end"], str]


class Emojis(TypedDict):
	icons: dict[Literal["loading", "wool", "sun", "inverted_clover", "capsule", "vibe", "sleep", "refresh", "penguin"], str]
	pancakes: dict[Literal["normal", "golden", "glitched"], str]
	treasures: dict[Literal["amber", "bottle", "card", "clover", "die", "journal", "pen", "shirt", "sun"], str]
	progress_bars: dict[Literal["square", "round"], ProgressBar]


def make_url(emoji: str, size: int = 4096, quality: str = "lossless") -> str:
	match = re.match(r'<(a?):([a-zA-Z0-9_]+):([0-9]+)>', emoji)
	if not match:
		raise ValueError("Invalid emoji")

	animated, name, emoji_id = match.groups()
	base_url = "https://cdn.discordapp.com/emojis/"
	return f"{base_url}{emoji_id}.{'gif' if animated else 'png'}?size={size}&quality={quality}"

def load_emojis() -> Emojis:
	with open("bot/data/emojis.yml", "r") as f:
		emojis_data = safe_load(f)
		return minify_emoji_names(emojis_data)


emojis: Emojis = load_emojis()
emoji_subs = []


def on_emojis_update(callback):
	emoji_subs.append(callback)

	def unsubscribe():
		if callback in emoji_subs:
			emoji_subs.remove(callback)
		else:
			raise ValueError(f"Subscription was already removed before.")

	return unsubscribe


def update_emojis(flat_key, emoji_value=None, remove=False):
	global emojis
	keys = flat_key.split('.')
	current_dict = emojis
	for part in keys[:-1]:
		current_dict = current_dict.setdefault(part, {})

	if remove:
		if keys[-1] in current_dict:
			del current_dict[keys[-1]]
	else:
		current_dict[keys[-1]] = emoji_value


def on_file_update(path):
	global emojis
	print(f"{colored('─ Reloading emojis.yml', 'yellow')}", end=" ─ ─ ─ ")
	old_emojis = emojis
	new_emojis = load_emojis()

	old_flat = flatten_emojis(old_emojis)
	new_flat = flatten_emojis(new_emojis)
	changes = []
	for key in [ key for key in old_flat if key not in new_flat ]:
		# removed
		changes.append(f"-{key}")
		update_emojis(key, remove=True)
	for key in [ key for key in new_flat if key not in old_flat ]:
		# added
		changes.append(f"+{key}")
		update_emojis(key, emoji_value=new_flat[key])
	for key in [ key for key in new_flat if key in old_flat and new_flat[key] != old_flat[key] ]:
		# modified
		changes.append(f"*{key}")
		update_emojis(key, emoji_value=new_flat[key])
	for callback in emoji_subs:
		callback(new_emojis)
	print("done", f"Changes: {', '.join(changes)}")


subscribe("emojis.yml", on_file_update)
