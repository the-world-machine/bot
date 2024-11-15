import os
import copy
import random
import aiohttp
import datetime
from PIL import Image
from io import BytesIO
from typing import Union, Optional
from collections.abc import Mapping
from interactions import Client, File

_yac: dict[str, Image.Image] = {}

async def get_image(url: str) -> Image.Image:
  if url in _yac:
    return Image.open(_yac[url])
  
  async with aiohttp.ClientSession() as session:
    async with session.get(url) as resp:
      if resp.status == 200:
        file = BytesIO(await resp.read())

        _yac[url] = file
        return Image.open(_yac[url])
      else:
        raise ValueError(f"{resp.status} Discord cdn shittig!!")

class FrozenDict(dict):
    def __init__(self, data):
        frozen_data = {k: self._freeze(v) for k, v in data.items()}
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

import copy
from typing import Union, Optional
import datetime

def rabbit(
  value: dict,
  raw_path: str,
  fallback_value: dict = None,
  _full_path: Optional[str] = None,
  raise_on_not_found: bool = True,
  _error_message: str | None = None,
  simple_error: bool = False,
  deepcopy: bool = False,
) -> Union[str, list, dict, int, bool, float, None, datetime.date, datetime.datetime]:
  """
  Retrieves a nested value from a dictionary based on a dot-separated path.
  Supports handling lists with indexed access (e.g., "somearray[0]").

  This function navigates through nested dictionaries according to the specified path. 
  If a key in the path is not found, it either returns an error message or raises an exception,
  depending on the `raise_on_not_found` parameter. Recursion is used to traverse nested levels.

  :param value: The dictionary to search within.
  :param raw_path: A dot-separated path string, where each segment represents a key at a deeper level. Can support list indices like "somearray[0]".
  :param fallback_value: A dictionary containing fallback values to use if a key is missing in `value`.
  :param raise_on_not_found: If `True`, raises a `ValueError` if a key in `raw_path` is not found. If `False`, returns an error message.
  :param _full_path: The original path (**you are not supposed to pass this**; it's for error reporting when `raw_path` is modified during recursion).
  :param _error_message: A custom error message template for missing keys. Use `[path]` to insert the full path in the error message, and `[error]` to get the specific error message.
  :param simple_error: If `True`, returns a simplified error message with just the path that failed, without highlighting. Defaults to `False` for highlighted error messages.
  :param deepcopy: Whether to do a deepcopy of the dicts/lists before returning.

  :returns: The value found at the specified path, or an error message if the path is invalid.
  :rtype: Union[str, list, dict, int, bool, float, None, datetime.date, datetime.datetime]

  :raises ValueError: If `raise_on_not_found` is `True` and a key in `raw_path` is not found in `value`.

  :notes: 
    - This function is recursive, meaning it calls itself when it finds nested dictionaries to navigate further.
    - If `raw_path` is empty, the function returns `value` as is.
    - List elements can be accessed using square brackets, e.g., "somearray[0]".
  """
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
      # First, try accessing the key/index from the main value
      if key is not None and index is not None:
        value = value[key][index]
        if fallback_value:
          fallback_value = fallback_value[key][index]  # Access from fallback value
      elif isinstance(value, dict) and key in value:
        value = value[key]
        if fallback_value and key in fallback_value:
          fallback_value = fallback_value[key]  # Access from fallback value
      else:
        if fallback_value and key in fallback_value:
          return fallback_value[key]  # Return from fallback_value if key not found in value
        else:
          raise KeyError(f"{key} not found")

      # Check if there are more segments in the path and if value/fallback_value are appropriate
      if len(parsed_path) > len(went_through) + 1:
        # Ensure value is a dictionary or list, or fallback_value is
        if not isinstance(value, (dict, list)) and not (fallback_value and isinstance(fallback_value, (dict, list))):
          error_msg = f"expected nested structure, found {type(value).__name__}"
          if not fallback_value and not simple_error:
            error_msg += f", no fallback passed"
          if fallback_value:
            error_msg += f", {type(fallback_value).__name__} in fallback"
          raise TypeError(error_msg)

    except (KeyError, IndexError, ValueError, TypeError) as e:
      failed_part = parsed_path[len(went_through)]
      
      before_failed = '.'.join(parsed_path[:len(went_through)])
      after_failed = '.'.join(parsed_path[len(went_through)+1:])
      
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

  # Perform deepcopy of value if necessary
  if deepcopy and isinstance(value, (dict, list)):
    value = copy.deepcopy(value)

  return value


async def set_random_avatar(client: Client):
    get_avatars = os.listdir('bot/images/profile_pictures')
    random_avatar = random.choice(get_avatars)

    avatar = File('bot/images/profile_pictures/' + random_avatar)

    await client.user.edit(avatar=avatar)
    return random_avatar