import asyncio
import re
import yaml as yaml
from pathlib import Path
from termcolor import colored
from traceback import print_exc
from dataclasses import dataclass
from datetime import datetime
from utilities.data_watcher import subscribe
from extensions.events.Ready import ReadyEvent
from typing import overload, TypeVar, Any, Type, Match
from utilities.emojis import emojis, flatten_emojis, on_emojis_update
from utilities.config import debugging, get_config, get_token, on_prod
from utilities.localization.icu import render_icu
from utilities.misc import FrozenDict, format_type_hint, decode_base64_padded, rabbit


_locales: dict[str, dict] = {}
debug: bool = bool(get_config("localization.debug", ignore_None=True))
if on_prod:
	debug = False if debug is not True else True
debug = debug if debug is not None else False

fallback_locale: dict[str, dict]


def local_override(locale: str, data: dict):
	_locales[locale] = FrozenDict(data)


def load_locale(locale: str):
	return yaml.full_load(open(Path('src/data/locales', locale + '.yml'), 'r', encoding='utf-8'))


last_update_timestamps = {}
debounce_interval = 1  # seconds


def on_file_update(filename):
	global fallback_locale
	current_time = datetime.now()
	locale = Path(filename).stem
	if filename in last_update_timestamps and (
	    current_time - last_update_timestamps[filename]
	).seconds < debounce_interval:
		return print(".", end="")
	last_update_timestamps[filename] = current_time
	print(colored(f'─ Reloading locale {locale}', 'yellow'), end="")
	try:
		hello = load_locale(locale)
		if hello is None:
			raise ValueError("Couldn't read for some reason?")
	except Exception as e:
		print(colored(" FAILED", "red"))
		print_exc()
		ReadyEvent.queue(e)
		return
	_locales[locale] = FrozenDict(hello)
	print(" ─ ─ ─ ")

	if locale == get_config("localization.main-locale"):
		fallback_locale = _locales[locale]


class UnknownLanguageError(Exception):
	...


def parse_locale(locale):
	if locale in _locales.keys():
		pass
	elif "-" in locale:
		locale_prefix = locale.split('-')[0]

		possible_locales = [ locale for locale in _locales.keys() if locale.startswith(locale_prefix) ]
		if len(possible_locales) == 0:
			locale = "en"

		for possible_locale in possible_locales:
			if possible_locale in _locales.keys():
				locale = possible_locale
				break
	elif locale not in _locales.keys():
		raise UnknownLanguageError(f"Language {locale} not found in {_locales.keys()}")
	return locale


def get_locale(locale):
	return _locales[parse_locale(locale)]


if debugging():
	print("Loading locales")
else:
	print("Loading locales ... \033[s", flush=True)

subscribe("locales/", on_file_update)
loaded = 0
for file in Path('src/data/locales').glob('*.yml'):
	name = file.stem
	try:
		_loaded = load_locale(name)
		if _loaded is None:
			raise ValueError("Couldn't read locale for some reason?")
		_locales[name] = FrozenDict(_loaded)
	except Exception as e:
		if get_config("localization.main-locale") == name:
			raise e
		if debugging():
			print("| FAILED " + name)
		print_exc()
		ReadyEvent.queue(e)

	if debugging():
		print("| " + name)
	loaded += 1
if not debugging():
	print(f"\033[udone ({loaded})", flush=True)
	print("\033[999B", end="", flush=True)
else:
	print(f"Done ({loaded})")

if get_config("localization.main-locale") in _locales:
	_uhh_loc = get_config("localization.main-locale")
	fallback_locale = get_locale(_uhh_loc)
	print(f"Loaded fallback locale ({_uhh_loc})")

trailing_dots_regex = re.compile(r"\.*$")

T = TypeVar('T')


@dataclass
class Localization:
	global debug
	global fallback_locale
	global _locales
	locale: str
	prefix: str
	ctx: Any

	def __init__(self, source: str | Any | None = None, prefix: str = ""):
		self.ctx: Any = None
		raw_locale: str | None

		if source is not None and not isinstance(source, str):
			# It's likely a context object
			self.ctx = source
			raw_locale = getattr(self.ctx, 'locale', None)
		else:
			raw_locale = source

		final_locale: str
		if raw_locale is None:
			final_locale = get_config("localization.main-locale")
		else:
			try:
				# It might be a discord.Locale object, so we stringify it
				final_locale = parse_locale(str(raw_locale))
			except UnknownLanguageError:
				final_locale = get_config("localization.main-locale")

		self.locale = final_locale
		self.prefix = prefix

	@overload
	async def l(self, path: str, *, typecheck: Type[T], **variables: Any) -> T:
		...

	@overload
	async def l(self, path: str, **variables: Any) -> str:
		...

	async def l(self, path: str, *, typecheck: Any = str, format: bool = True, **variables: Any) -> Any:
		path = f"{trailing_dots_regex.sub('', self.prefix)}.{path}" if len(self.prefix) > 0 else path
		result = await self.sl(
		    path=path, locale=self.locale, typecheck=typecheck, format=format, ctx=self.ctx, **variables
		)
		return result

	@staticmethod
	@overload
	async def sl(
	    path: str,
	    locale: str | None,
	    *,
	    typecheck: Type[T],
	    raise_on_not_found: bool = False,
	    ctx: Any = None,
	    format: bool = True,
	    **variables: Any
	) -> T:
		...

	@staticmethod
	@overload
	async def sl(path: str, locale: str | None, *, ctx: Any = None, **variables: Any) -> str:
		...

	@staticmethod
	async def sl(
	    path: str,
	    locale: str | None = None,
	    *,  # ← makes all next args only accepted as keyword arguments
	    typecheck: Any = str,
	    raise_on_not_found: bool = False,
	    ctx: Any = None,
	    format: bool = True,
	    **variables: Any
	) -> Any:
		if locale is None:
			raise ValueError("No locale provided")
		value = get_locale(locale)
		result = raw_result = rabbit(
		    value,
		    path,
		    fallback_value=fallback_locale if 'fallback_locale' in globals() and fallback_locale else None,
		    raise_on_not_found=raise_on_not_found,
		    _error_message="[path] ([error])" if debug else "[path]"
		)
		if format:
			result = await assign_variables(raw_result, locale, ctx=ctx, **variables)

		if not typecheck == Any and not isinstance(result, typecheck):
			if result == None:
				return "{path} not found in all attempted languages"
			raise TypeError(
			    f"Expected {format_type_hint(typecheck)}, got {format_type_hint(type(result))} for path '{path}'"
			)
		return result

	@staticmethod
	async def sl_all(localization_path: str, raise_on_not_found: bool = False, **variables: Any) -> dict[str, Any]:
		results = {}

		for locale in _locales.keys():
			value = get_locale(locale)
			value = rabbit(
			    value,
			    localization_path,
			    raise_on_not_found=raise_on_not_found,
			    _error_message="[path] ([error], debug mode ON)" if debug else "[path]"
			)

			results[locale] = await assign_variables(value, locale, **variables)

		return results


token = get_token()
bot_id = decode_base64_padded(token.split('.')[0])
@overload
async def assign_variables(
    input: str, locale: str | None = ..., pretty_numbers: bool = ..., *, ctx: Any = None, **variables: Any
) -> str:
	...


@overload
async def assign_variables(
    input: T, locale: str | None = ..., pretty_numbers: bool = ..., *, ctx: Any = None, **variables: Any
) -> T:
	...

async def assign_variables(
    input: Any,
    locale: str | None = None,
    pretty_numbers: bool = True,
    *,
    ctx: Any = None,
    **variables: Any
) -> Any:
	if locale is None:
		locale = get_config("localization.main-locale")
	if isinstance(input, str):
		return await render_icu(input, variables, locale, ctx)
	elif isinstance(input, tuple):
		out = []
		for elem in input:
			out.append((await assign_variables(elem, locale, pretty_numbers=pretty_numbers, ctx=ctx, **variables)))
		return tuple(out)
	elif isinstance(input, dict):
		new_dict = {}
		for key, value in input.items():
			new_dict[key] = await assign_variables(value, locale, pretty_numbers=pretty_numbers, ctx=ctx, **variables)
		return new_dict
	else:
		return input
