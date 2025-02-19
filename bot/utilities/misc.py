import io
import copy
import numpy
import aiofiles
import aiohttp
import datetime
import subprocess
from PIL import Image
from pathlib import Path
from numpy.typing import NDArray
from typing import Literal, Union, Optional
from interactions import Activity, ActivityType, Client, File, StringSelectMenu, StringSelectOption, User


class FrozenDict(dict):

	def __init__(self, data):
		if not isinstance(data, (dict, list, tuple)):
			raise ValueError(f"Value must be a dict, list or a tuple. Received {type(data)}")
		frozen_data = { k: self._freeze(v) for k, v in data.items() }
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


def _convert(bytes: bytes, to: Literal["numpy_buffer", "bytesio"]) -> NDArray[numpy.float64] | str | io.BytesIO:
	match to:
		case "numpy_buffer":
			return numpy.frombuffer(bytes, dtype=numpy.uint8)
		case "bytesio":
			return io.BytesIO(bytes)


class InvalidResponseError(Exception):
	...


async def fetch(url: str):
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as resp:
			if 200 <= resp.status < 300:
				return await resp.read()
			else:
				raise InvalidResponseError(f"{resp.status} website shittig!!")


async def read_file(path: Path):
	async with aiofiles.open(path, "rb") as f:
		return await f.read()


cache: dict[str, bytes] = {}


async def cached_get(
    location: str | Path,
    force: bool = False,
    convert: Literal["numpy_buffer", "bytesio", "nop"] = "bytesio"
) -> NDArray[numpy.float64] | str | io.BytesIO | bytes:
	loki = str(location)
	is_file = Path(location).is_file()
	if is_file:
		location = Path(location).absolute()

	if force or loki not in cache:
		cache[loki] = await read_file(location) if is_file else await fetch(loki)

	if convert == "nop":
		return cache[loki]

	return _convert(cache[loki], to=convert)

def rabbit(
    value: dict,
    path: str,
    fallback_value: dict = None,
    _full_path: Optional[str] = None,
    return_None_on_not_found: bool = False,
    raise_on_not_found: bool = True,
    _error_message: str | None = None,
    simple_error: bool = False,
    deepcopy: bool = False,
) -> Union[str, list, dict, int, bool, float, None, datetime.date, datetime.datetime]:
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
	path = None
	if return_None_on_not_found and raise_on_not_found:
		raise StupidError("the passed arguments make total sense")
	if not _error_message:
		_error_message = "Rabbit fail [path] ([error])"
	if not _full_path:
		_full_path = raw_path
	if not raw_path:
		return value
	parsed_path = raw_path.split('.')
	went_through = []
	key = None
	index = None

	for path in parsed_path:
		if '[' in path and ']' in path:
			key, index = path.split('[')
			index = int(index[:-1])
		else:
			key = path
			index = None
		try:
			if key is not None and index is not None:
				value = value[key][index]
				if fallback_value:
					fallback_value = fallback_value[key][index]
			elif isinstance(value, dict):
				if key in value:
					value = value[key]
				else:
					value = None
				if fallback_value:
					fallback_value = fallback_value[key]
			else:
				raise KeyError(f"{key} not found")

			if value == None:
				value = fallback_value
			if value == None:
				raise KeyError(f"{key} not found")
			if len(parsed_path) > len(went_through) + 1:
				if not isinstance(value,
				                  (dict, list)) and not (fallback_value and isinstance(fallback_value, (dict, list))):
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

	if deepcopy and isinstance(value, (dict, list)):
		return copy.deepcopy(value)

	return value


def exec(command: list) -> str:
	return subprocess.run(
	    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
	).stdout  # TODO: eror handling


def shell(command: str) -> str:
	return exec([ "sh", "-c", command ])


def get_git_hash(long: bool = False) -> str:
	return exec(x for x in [ 'git', 'rev-parse', '--short' if not long else None, 'HEAD'] if x is not None).strip()


def get_current_branch() -> str:
	return exec([ 'git', 'branch', '--show-current']).strip()


async def set_status(client: Client, text: str | list):
	from utilities.localization import assign_variables
	if text is not None:
		status = assign_variables(
		    input=text,
		    shard_count=1 if not hasattr(client, "shards") else len(client.shards),
		    guild_count=len(client.guilds),
		    token=client.token
		)
	await client.change_presence(activity=Activity("meow", type=ActivityType.CUSTOM, state=status))
	return status


async def set_avatar(client: Client, avatar: File | Path | str):
	return await client.user.edit(avatar=avatar)


def make_empty_select(loc, placeholder: str = None):
	return StringSelectMenu(
	    *[StringSelectOption(label=loc.l("general.select.empty"), value="423")], placeholder=placeholder, disabled=True
	)


def pretty_user(user: User):
	return f"({user.username}) {user.display_name}" if user.display_name != user.username else user.username
