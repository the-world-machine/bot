from io import BytesIO
from typing import Union
from PIL import Image
import aiohttp
import datetime

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
      
def rabbit(
  value: dict,
  raw_path: str,
  fallback_value: dict = None,
  _full_path: str = None,
  raise_on_not_found: bool = False,
  _error_message: str = "Rabbit could not find [path]",
  simple_error: bool = False,
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
  :param _error_message: A custom error message template for missing keys. Use `[path]` to insert the full path in the error message.
  :param simple_error: If `True`, returns a simplified error message with just the path that failed, without highlighting. Defaults to `False` for highlighted error messages.

  :returns: The value found at the specified path, or an error message if the path is invalid.
  :rtype: Union[str, list, dict, int, bool, float, None, datetime.date, datetime.datetime]

  :raises ValueError: If `raise_on_not_found` is `True` and a key in `raw_path` is not found in `value`.

  :notes: 
    - This function is recursive, meaning it calls itself when it finds nested dictionaries to navigate further.
    - If `raw_path` is empty, the function returns `value` as is.
    - List elements can be accessed using square brackets, e.g., "somearray[0]".
  """
  if not _full_path:
    _full_path = raw_path
  if not raw_path:
    return value

  parsed_path = raw_path.split('.')
  went_through = []

  for path in parsed_path:
    array = False
    if '[' in path and ']' in path:
      key, index = path.split('[')
      index = int(index[:-1])
      array = True
  
    try:
      if array:
        value = value[key][index]
      elif isinstance(value, dict):
        value = value[path]
      else:
        return rabbit(value, '.'.join(parsed_path[len(went_through) + 1:]), fallback_value, _full_path, raise_on_not_found, _error_message, simple_error)
    except (KeyError, IndexError, ValueError) as e:
      failed_part = parsed_path[len(went_through)]
      
      before_failed = '.'.join(parsed_path[:len(went_through)])
      after_failed = '.'.join(parsed_path[len(went_through)+1:])
      
      if simple_error:
        error_message = _error_message.replace("[path]", f"{before_failed}.{failed_part}{'.' + after_failed if after_failed else ''}")
      else:
        if before_failed:
          full_error_path = f"`{before_failed}.`**{failed_part}**`"
        else:
          full_error_path = f"`**{failed_part}**`"
        
        if after_failed:
          full_error_path += f".{after_failed}`"
        
        error_message = _error_message.replace("[path]", full_error_path)
    
      if raise_on_not_found:
        raise ValueError(error_message)
      return error_message
    
    went_through.append(path)

  return value

