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


def parse_path(raw_path: str):
	pattern = r'([\'"])(.*?)\1|([^./]+)'  # haven't tested quotes with quotes inside (i dont rememebr the regex for backslash escaping)

	parts = []
	for match in re.finditer(pattern, raw_path):
		if match.group(1):  # quoted group
			parts.append(match.group(2))  # content inside quotes
		else:  # normal group
			parts.append(match.group(3))

	return parts


def rabbit(
    value: dict,
    path: str,
    fallback_value: dict | None = None,
    _full_path: Optional[str] = None,
    return_None_on_not_found: bool = False,
    raise_on_not_found: bool = True,
    _error_message: str | None = None,
    simple_error: bool = False,
    deepcopy: bool = False,
) -> Union[str, tuple, dict, int, bool, float, None, datetime.date, datetime.datetime]:
	"""
  Goes down the `value`'s tree based on a dot-separated, or [0] indexed `path` string.

  It either returns the found value itself, or an error message as the value. You can customize the error message with the `_error_message` argument

  :param value: The dictionary to search within
  :param raw_path: A dot-separated path string, where each segment represents a key at a deeper level. Can support list indices like "somearray[0]"
  :param raise_on_not_found: If `True`, raises a `ValueError` if a key in `raw_path` is not found. If `False`, returns the error message as str
  :param _error_message: A custom error message template for missing keys. Use `[path]` to insert the full path in the error message, and `[error]` to get the specific error message
  
  :param _full_path: do not pass this thanks

  :returns: The value the rabbit ended up on

  :raises ValueError: If `raise_on_not_found` is `True` and a key in `raw_path` is not found in `value`

  :notes: 
    - If `raw_path` is empty, the function returns `value` as is
    - List elements are accessed using square brackets, e.g. "somearray[0]"
  """
	raw_path = path
	if return_None_on_not_found and raise_on_not_found:
		raise StupidError("the passed arguments make total sense")
	if not _error_message:
		_error_message = "Rabbit fail [path] ([error])"
	if not _full_path:
		_full_path = raw_path
	if not raw_path:
		return value
	went_through = []
	key = None
	index = None

	parsed_path = parse_path(raw_path)
	for path in parsed_path:
		if '[' in path and ']' in path:
			key, index = path.split('[')
			index = int(index[:-1])
		else:
			key = path
			index = None
		try:
			if key is not None and index is not None:
				value = value[key][index]  # type: ignore
				if fallback_value:
					fallback_value = fallback_value[key][index]  # type: ignore
			elif isinstance(value, dict):
				if key in value:
					value = value[key]
				else:
					value = None  # type: ignore
				if fallback_value:
					fallback_value = fallback_value[key]  # type: ignore
			else:
				raise KeyError(f"{key} not found")

			if value == None:
				value = fallback_value  # type: ignore
			if value == None:
				raise KeyError(f"{key} not found")
			if len(parsed_path) > len(went_through) + 1:
				if not isinstance(value,
				                  (dict,
				                   tuple)) and not (fallback_value and isinstance(fallback_value, (dict, tuple))):
					error_msg = f"expected nested structure, found {type(value).__name__}"
					if not fallback_value and not simple_error:
						error_msg += f", no fallback passed"
					if fallback_value:
						error_msg += f", {type(fallback_value).__name__} in fallback"
					raise TypeError(error_msg)

		except (KeyError, IndexError, ValueError, TypeError, StupidError) as e:
			if return_None_on_not_found and not raise_on_not_found:
				return None
			failed_part = parsed_path[len(went_through)]

			before_failed = '.'.join(parsed_path[:len(went_through)])
			after_failed = '.'.join(parsed_path[len(went_through) + 1:])

			if simple_error:
				error_message = f"{before_failed}.{failed_part}{'.' + after_failed if after_failed else ''}"
			else:
				if before_failed:
					full_error_path = f"`{before_failed}.`**`{failed_part}`**"
				else:
					full_error_path = f"**`{failed_part}`**"

				if after_failed:
					full_error_path += f"`.{after_failed}`"

				error_message = _error_message.replace("[path]", full_error_path).replace("[error]", str(e))

			if raise_on_not_found:
				raise ValueError(error_message)
			return error_message

		went_through.append(path)

	if deepcopy and isinstance(value, (dict, tuple)):
		return copy.deepcopy(value)

	return value


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
	    *[StringSelectOption(label=loc.l("general.select.empty"), value="423")], placeholder=placeholder, disabled=True
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
