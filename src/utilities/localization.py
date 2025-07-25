import re
import asyncio
import yaml.parser
import yaml as yaml
from babel import Locale
from pathlib import Path
from termcolor import colored
from dataclasses import dataclass
from datetime import datetime, timedelta
from babel.dates import format_timedelta
from humanfriendly import format_timespan
from utilities.data_watcher import subscribe
from extensions.events.Ready import ReadyEvent
from utilities.database.schemas import UserData
from utilities.misc import FrozenDict, decode_base64_padded, rabbit
from utilities.emojis import emojis, flatten_emojis, on_emojis_update
from utilities.config import debugging, get_config, get_token, on_prod
from typing import overload, Union, TypeVar, Any, Literal, Generic, Optional, Type
from functools import wraps

emoji_dict = {}


def edicted(emojis):
	global emoji_dict
	f_emojis = flatten_emojis(emojis)
	emoji_dict = { f'emoji:{name.replace("icons.", "")}': f_emojis[name] for name in f_emojis }


edicted(emojis)
on_emojis_update(edicted)

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
	except Exception as e:
		print(colored(" FAILED", "red"))
		print(ReadyEvent)
		ReadyEvent.log(e)
		return
	_locales[locale] = hello
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
		_locales[name] = FrozenDict(load_locale(name))
	except Exception as e:
		if get_config("localization.main-locale") == name:
			raise e
		if debugging():
			print("| FAILED " + name)
		ReadyEvent.log(e)

	if debugging():
		print("| " + name)
	loaded += 1
if not debugging():
	print(f"\033[udone ({loaded})", flush=True)
	print("\033[999B", end="", flush=True)
else:
	print(f"Done ({loaded})")

if get_config("localization.main-locale") in _locales:
	fallback_locale = get_locale(get_config("localization.main-locale"))

trailing_dots_regex = re.compile(r"\.*$")

T = TypeVar('T')


@dataclass
class Localization:
	global debug
	global fallback_locale
	global _locales
	locale: str
	prefix: str

	def __init__(self, locale: str | None = None, prefix: str = ""):
		final_locale: str
		if locale is None:
			final_locale = get_config("localization.main-locale")
		else:
			try:
				final_locale = parse_locale(locale)
			except UnknownLanguageError:
				final_locale = get_config("localization.main-locale")
		self.locale = final_locale
		self.prefix = prefix

	def l(self, path: str, typecheck: Optional[Type[T]] = None, **variables: Any) -> Union[str, list[str], dict, T]:
		path = f"{trailing_dots_regex.sub('', self.prefix)}.{path}" if len(self.prefix) > 0 else path
		result = self.sl(path=path, locale=self.locale, **variables)

		if typecheck is not None and not isinstance(result, typecheck):
			raise TypeError(f"Expected {typecheck.__name__}, got {type(result).__name__} for path '{path}'")
		return result

	@staticmethod
	def sl(
	    path: str,
	    locale: str | None = None,
	    typecheck: Optional[Type[T]] = None,
	    raise_on_not_found: bool = False,
	    **variables: Any
	) -> Union[str, list[str], dict, T]:
		if locale is None:
			raise ValueError("No locale provided")

		value = get_locale(locale)
		raw_result = rabbit(
		    value,
		    path,
		    fallback_value=fallback_locale if 'fallback_locale' in globals() and fallback_locale else None,
		    raise_on_not_found=raise_on_not_found,
		    _error_message="[path] ([error])" if debug else "[path]"
		)

		result = assign_variables(raw_result, locale, **variables)

		if typecheck is not None and not isinstance(result, typecheck):
			raise TypeError(f"Expected {typecheck.__name__}, got {type(result).__name__} for path '{path}'")
		return result

	@staticmethod
	def sl_all(localization_path: str, raise_on_not_found: bool = False, **variables: Any) -> dict[str, Any]:
		results = {}

		for locale in _locales.keys():
			value = get_locale(locale)
			value = rabbit(
			    value,
			    localization_path,
			    raise_on_not_found=raise_on_not_found,
			    _error_message="[path] ([error], debug mode ON)" if debug else "[path]"
			)

			results[locale] = assign_variables(value, locale, **variables)

		return results


def fnum(num: float | int, locale: str = "en", ordinal: bool = False) -> str:
	if isinstance(num, float):
		fmtd = '{:,.3f}'.format(num)
	else:
		fmtd = '{:,}'.format(num)
	if locale in ("ru", "uk", "be", "kk", "ro", "sr", "bg"):
		fmtd = fmtd.replace(",", " ")

	if ordinal and isinstance(num, int) and locale not in ("ru", "uk", "be", "kk", "ro", "sr", "bg"):
		fmtd += english_ordinal_for(num)

	return fmtd


def ftime(
    duration: timedelta | float,
    locale: str = "en",
    bold: bool = True,
    format: Literal['narrow', 'short', 'medium', 'long'] = "narrow",
    max_units: int = 69,
    minimum_unit: Literal["year", "month", "week", "day", "hour", "minute", "second"] = "second",
    **kwargs
) -> str:
	locale = Locale.parse(locale, sep="-").language

	if isinstance(duration, (int, float)):
		duration = timedelta(seconds=duration)

	formatted = format_timespan(duration, max_units=max_units).replace(" and", ",")

	unit_hierarchy = [ "year", "month", "week", "day", "hour", "minute", "second"]
	min_unit_index = unit_hierarchy.index(minimum_unit)

	def translate_unit(component: str) -> str:
		amount, unit = component.split(" ", 1)

		if not unit.endswith('s'):
			unit += "s"

		amount = float(amount)
		if unit == "years":
			unit = "weeks"
			amount *= 52.1429

		translated_component = format_timedelta(timedelta(**{ unit: amount}), locale=locale, format=format, **kwargs)
		return translated_component

	filtered_components = [
	    part for part in formatted.split(", ")
	    if unit_hierarchy.index(part.split(" ", 1)[1].rstrip('s')) <= min_unit_index
	]

	translated = ", ".join([translate_unit(part) for part in filtered_components])

	if bold:
		translated = re.sub(r'(\d+)', r'**\1**', translated)
	return translated


def english_ordinal_for(n: int | float):
	if isinstance(n, float):
		n = int(str(n).split('.')[1][0])

	if 10 <= int(n) % 100 <= 20:
		suffix = 'th'
	else:
		suffix = { 1: 'st', 2: 'nd', 3: 'rd'}.get(int(n) % 10, 'th')

	return suffix


token = get_token()
bot_id = decode_base64_padded(token.split('.')[0])


def assign_variables(input: Any, locale: str = get_config("localization.main-locale"), **variables: Any):
	if isinstance(input, str):
		result = input
		for name, data in {
		    **variables,
		    **emoji_dict,
		    **{
		        'app:mention': f"<@{bot_id}>",
		        'app:id': str(bot_id)
		    }
		}.items():
			if isinstance(data, (int, float)):
				data = fnum(data, locale)
			elif not isinstance(data, str):
				data = str(data)

			result = result.replace(f'[{name}]', data)
		return result
	elif isinstance(input, list):
		processed = []
		for elem in input:
			processed.append(assign_variables(elem, locale, **variables))
		return processed
	elif isinstance(input, dict):
		new_dict = {}
		for key, value in input.items():
			new_dict[key] = assign_variables(value, locale, **variables)
		return new_dict
	else:
		return input


limits = {
    "treasure.tip": 5,
    "nikogotchi.tipnvalid": 5,
    "nikogotchi.found.renamenote": 5,
    "wool.transfer.errors.note_nuf": -1,
    "settings.errors.channel_lost_warn": -1,
    "wool.transfer.to.bot.notefirmation": 10,
    "settings.welcome.enabled.default_tip": 15,
    "settings.welcome.editor.disabled_note": 15,
    "nikogotchi.treasured.dialogues.senote": 25,
}


async def put_mini(
    loc: Localization,
    message: str,
    user_id: str | int | None = None,
    type: Literal["note", "tip", "warn", "err"] = "note",
    pre: str = "",
    markdown: bool = True
) -> str:
	if user_id:
		user_data = await UserData(str(user_id)).fetch()
		reacher = user_data.minis_shown.get(message, 0)
		if limits.get(message) != -1 and limits.get(message, 0) <= reacher:
			return ""
		asyncio.create_task(user_data.minis_shown.increment_key(message))
	name = loc.l(f"general.minis.{type}")
	msg = loc.l(message)
	return f"{pre}{'-# ' if markdown else ''}{name} {msg}"


def amperjoin(items: list):
	items = list(map(str, items))
	if len(items) == 0:
		return ""
	if len(items) == 1:
		return f"{items[0]}"
	if len(items) == 2:
		return " & ".join(items)
	return ", ".join(items[:-1]) + " & " + items[-1]
