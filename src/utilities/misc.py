import io
import copy
import re
import aiohttp
import aiofiles
import datetime
import subprocess
from pathlib import Path
from base64 import b64decode
from typing import Any, TypedDict, Union, Optional, get_args, get_origin
from jellyfish import jaro_winkler_similarity, levenshtein_distance
from interactions import Activity, ActivityType, Client, File, StringSelectMenu, StringSelectOption, User


class FrozenDict(dict):

	def __init__(self, data):
		if not isinstance(data, (dict, list, tuple)):
			raise ValueError(f"Value must be a dict, list or a tuple. Received {type(data)}")
		if isinstance(data, dict):
			frozen_data = { k: self._freeze(v) for k, v in data.items() }
		elif isinstance(data, list):
			frozen_data = { i: self._freeze(item) for i, item in enumerate(data) }
		elif isinstance(data, tuple):
			frozen_data = { i: self._freeze(item) for i, item in enumerate(data) }
		super().__init__(frozen_data)

	def _freeze(self, value):
		"""Recursively convert dictionaries to FrozenDict and lists to tuples."""
		if isinstance(value, dict):
			return FrozenDict(value)
		elif isinstance(value, list):
			return tuple(self._freeze(item) for item in value)
		elif isinstance(value, tuple):
			return tuple(self._freeze(item) for item in value)
		else:
			return value

	def __setitem__(self, key, value):
		raise TypeError("FrozenDict is immutable")

	def __delitem__(self, key):
		raise TypeError("FrozenDict is immutable")

	def clear(self):
		raise TypeError("FrozenDict is immutable")

	def pop(self, key, default=None):
		raise TypeError("FrozenDict is immutable")

	def popitem(self):
		raise TypeError("FrozenDict is immutable")

	def setdefault(self, key, default=None):
		raise TypeError("FrozenDict is immutable")

	def update(self, *args, **kwargs):
		raise TypeError("FrozenDict is immutable")

	def __repr__(self):
		return f"FrozenDict({super().__repr__()})"


class StupidError(Exception):
	...


class InvalidResponseError(Exception):
	...


async def fetch(url: str):
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as resp:
			if 200 <= resp.status < 300:
				return await resp.read()
			else:
				raise InvalidResponseError(f"{resp.status} website shittig!!")


async def read_file(path: Path | str):
	async with aiofiles.open(path, "rb") as f:
		return await f.read()


cache: dict[str, bytes] = {}


async def cached_get(location: str | Path, force: bool = False, raw: bool = False) -> io.BytesIO | bytes:
	loki = str(location)
	is_file = Path(location).is_file()
	if is_file:
		location = Path(location).absolute()

	if location is str and (not location.startswith("https://") or not location.startswith("http://")):
		raise ValueError("invalid url")

	if force or loki not in cache:
		cache[loki] = await read_file(Path(location)) if is_file else await fetch(loki)

	return cache[loki] if raw else io.BytesIO(cache[loki])


def parse_path(raw_path: str) -> list[Union[str, int]]:
	"""
    Parses a path string into a list of keys and indices.
    e.g., 'interactions.phrases[0]["user-key"][1]' -> ['interactions', 'phrases', 0, 'user-key', 1]
    """
	if not raw_path:
		return []
	pattern = r"[\w-]+|\[\d+\]|\[['\"].*?['\"]\]"
	raw_parts = re.findall(pattern, raw_path)

	cleaned_parts = []
	for part in raw_parts:
		if part.startswith('[') and part.endswith(']'):
			content = part[1:-1]
			if content.isdigit() or (content.startswith('-') and content[1:].isdigit()):
				cleaned_parts.append(int(content))
			else:
				cleaned_parts.append(content[1:-1])
		else:
			cleaned_parts.append(part)
	return cleaned_parts


def rabbit(
    value: dict,
    path: str,
    fallback_value: Optional[dict] = None,
    _full_path: Optional[str] = None,
    return_None_on_not_found: bool = False,
    raise_on_not_found: bool = True,
    _error_message: Optional[str] = None,
    simple_error: bool = False,
    deepcopy: bool = False,
) -> Any:
	"""
    Goes down the `value`'s tree based on a dot-separated, or [0] indexed `path` string.

    It either returns the found value itself, or an error message as the value. You can customize the error message with the `_error_message` argument.

    :param value: The dictionary to search within.
    :param path: A dot-separated path string. Supports list indices ("list[0]"), nested indices ("list[0][1]"), and quoted keys ("dict['key-name']").
    :param fallback_value: A secondary dictionary to search in if a value is None at any point in the path.
    :param return_None_on_not_found: If True, returns None if any part of the path is not found. Overrides raise_on_not_found.
    :param raise_on_not_found: If True, raises a ValueError if a key/index in `path` is not found.
    :param _error_message: A custom error message template. Use `[path]` for the full path and `[error]` for the specific error.
    :param simple_error: If True, returns a simplified error string showing the path.
    :param deepcopy: If True, returns a deep copy of the found value if it's a dict, list, or tuple.
    :param _full_path: (Internal use) The original full path for error messages.

    :return: The value at the specified path, None, or an error string.
    :raises ValueError: If `raise_on_not_found` is True and a key/index is not found.
    :raises StupidError: If `return_None_on_not_found` and `raise_on_not_found` are both True.
    """
	raw_path = path
	if return_None_on_not_found and raise_on_not_found:
		raise StupidError("return_None_on_not_found and raise_on_not_found cannot both be True.")

	_error_message = _error_message or "Rabbit fail [path] ([error])"
	_full_path = _full_path or raw_path

	parsed_path = parse_path(raw_path)
	if not parsed_path:
		return value

	current_value = value
	current_fallback = fallback_value

	for i, part in enumerate(parsed_path):
		try:
			if isinstance(part, int):
				current_value = current_value[part]
			else:
				current_value = current_value[part]

			if current_fallback is not None:
				try:
					if isinstance(part, int):
						current_fallback = current_fallback[part]
					else:
						current_fallback = current_fallback[part]
				except (KeyError, IndexError, TypeError):
					current_fallback = None

			if current_value is None and current_fallback is not None:
				current_value = current_fallback

			if current_value is None and i < len(parsed_path) - 1:
				raise KeyError(f"Path leads to None at '{part}' before reaching the end")

		except (KeyError, IndexError, TypeError) as e:
			if return_None_on_not_found:
				return None

			def format_part_for_error(p: Union[str, int], is_first: bool = False) -> str:
				if isinstance(p, int):
					return f"[{p}]"
				return str(p) if is_first else f".{p}"

			path_parts_str = [format_part_for_error(p, i == 0) for i, p in enumerate(parsed_path)]

			before_path = "".join(path_parts_str[:i])
			failed_part_str = path_parts_str[i].lstrip('.')
			after_path = "".join(path_parts_str[i + 1:])

			if simple_error:
				error_message = f"{before_path}{failed_part_str}{after_path}"
			else:
				full_error_path = f"`{before_path}`**`{failed_part_str}`**"
				if after_path:
					full_error_path += f"`{after_path}`"
				error_message = _error_message.replace("[path]", full_error_path).replace("[error]", str(e))

			if raise_on_not_found:
				raise ValueError(error_message) from e
			return error_message

	if deepcopy and isinstance(current_value, (dict, list, tuple)):
		return copy.deepcopy(current_value)

	return current_value

def exec(command: list) -> str:
	return subprocess.run(
	    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
	).stdout  # TODO: eror handling


def shell(command: str) -> str:
	return exec([ "sh", "-c", command ])


def get_git_hash(long: bool = False) -> str:
	return exec([ x for x in [ 'git', 'rev-parse', '--short' if not long else None, 'HEAD'] if x is not None ]).strip()


def get_current_branch() -> str:
	return exec([ 'git', 'branch', '--show-current']).strip()


async def set_status(client: Client, text: str | list | None):
	from utilities.localization import assign_variables
	if text is not None:
		status = str(
		    assign_variables(
		        input=text,
		        shard_count=len(client.shards) if hasattr(client, "shards") else 1,  # type: ignore
		        guild_count=len(client.guilds),
		        token=client.token
		    )
		)
	await client.change_presence(activity=Activity(name="meow", type=ActivityType.CUSTOM, state=status))
	return status


async def set_avatar(client: Client, avatar: File | Path | str):
	return await client.user.edit(avatar=avatar)


def make_empty_select(loc, placeholder: str | None = None):
	return StringSelectMenu(
	    *[StringSelectOption(label=loc.l("global.select.empty"), value="423")], placeholder=placeholder, disabled=True
	)


def pretty_user(user: User):
	return f"({user.username}) {user.display_name}" if user.display_name != user.username else user.username


def decode_base64_padded(s):
	missing_padding = len(s) % 4
	if missing_padding:
		s += '=' * (4 - missing_padding)
	return b64decode(s).decode("utf-8")


class Option(TypedDict):
	names: Optional[list[str]]
	picked_name: str
	value: str


def optionSearch(query: str, options: list[Option]) -> list[dict[str, str]]:
	matches = []
	top = []

	filtered_options = [
	    option for option in options
	    if any(name.lower().startswith(query.lower()) for name in (option.get("names") or [option["picked_name"]]))
	]

	if filtered_options:
		options = filtered_options

	for option in options:
		name_candidates = option.get("names") or [option["picked_name"]]
		best_name = min(name_candidates, key=lambda name: levenshtein_distance(query, name))

		if levenshtein_distance(query, best_name) == 0:
			top.append({ "name": option["picked_name"], "value": option["value"]})
		elif query.lower() in best_name.lower():
			matches.append({ "name": option["picked_name"], "value": option["value"]})
		else:
			jaro_similarity = jaro_winkler_similarity(query.lower(), best_name.lower())
			if jaro_similarity >= 0.5:
				matches.append({ "name": option["picked_name"], "value": option["value"]})

	matches.sort(key=lambda x: levenshtein_distance(query.lower(), x["name"].lower()))

	return top + matches

def format_type_hint(type_hint: Any) -> str:
	"""Formats a type hint for clean error messages."""
	if hasattr(type_hint, '__name__'):
		return type_hint.__name__
	return str(type_hint)
