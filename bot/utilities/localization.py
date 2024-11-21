import re
from babel import Locale
from pathlib import Path
from termcolor import colored
from yaml import safe_load
from datetime import timedelta
from dataclasses import dataclass
from typing import Literal, Union
from utilities.config import get_config
from babel.dates import format_timedelta
from humanfriendly import format_timespan
from utilities.data_watcher import subscribe
from utilities.misc import FrozenDict, rabbit
from utilities.emojis import emojis, flatten_emojis, on_emojis_update

emoji_dict = {}
def edicted(emojis):
	global emoji_dict
	f_emojis = flatten_emojis(emojis)
	emoji_dict = {f'emoji:{name.replace("icons.", "")}': f_emojis[name] for name in f_emojis}
edicted(emojis)
on_emojis_update(edicted)

_locales = {}
debug: bool = False
fallback_locale: str = None

def local_override(locale: str, data: dict):
	_locales[locale] = FrozenDict(data)

def load_locale(locale: str):
	with open(Path('bot/data/locales', locale+'.yml'), 'r', encoding='utf-8') as f:
			return safe_load(f)
	
def on_file_update(filename):
	global fallback_locale
	locale = Path(filename).stem
	text = f'─ Reloading locale {locale}'
	print(f"{colored(text, 'yellow')}", end=" ─ ─ ─ ")
	_locales[locale] = FrozenDict(load_locale(locale))
	if locale == get_config("localization.main-locale"):
		fallback_locale = _locales[locale]
	print("done")


def get_locale(locale):
	if locale in _locales.keys():
		pass
	elif "-" in locale:
		locale_prefix = locale.split('-')[0]
		
		possible_locales = [locale for locale in _locales.keys() if locale.startswith(locale_prefix)]
		
		for possible_locale in possible_locales:
			if possible_locale in _locales.keys():
				locale = possible_locale
				break
	else:
			locale = "en"
	return _locales[locale]


print("Loading locales...")

subscribe("locales/", on_file_update)
loaded = 0
for file in Path('bot/data/locales').glob('*.yml'):
	name = file.stem
	_locales[name] = load_locale(name)
	print("| "+name)
	loaded += 1
print(f"Done ({loaded})")

if not get_config("localization.debug"):
	debug = True
	fallback_locale = get_locale(get_config("localization.main-locale"))

@dataclass
class Localization:
	global debug
	global fallback_locale
	global _locales

	locale: str
	def __init__(self, ctx):
		self.locale = ctx.locale
	
	def l(self, localization_path: str, **variables: dict[str, any]) -> Union[str, list[str], dict]:
		return self.sl(localization_path=localization_path, locale=self.locale, **variables)
	
	@staticmethod
	def sl(localization_path: str, locale: str, raise_on_not_found: bool = False, self = None, **variables: dict[str, any]) -> Union[str, list[str], dict]:
		""" Static version of .l for single use (where making another Localization() makes it cluttery)"""
		if locale == None:
			raise ValueError("No locale provided")
		
		value = get_locale(locale)

		value = rabbit(value, 
					   localization_path, 
					   fallback_value=fallback_locale if fallback_locale else None, 
					   raise_on_not_found=raise_on_not_found,
					   _error_message="[path] ([error], debug mode ON)" if debug else "[path]")
		
		return assign_variables(value, locale, **variables)

	@staticmethod
	def sl_all(localization_path: str, raise_on_not_found: bool = False, **variables: str) -> dict[str, Union[str, list[str], dict]]:
		results = {}
		
		for locale in _locales.keys():
			value = get_locale(locale)
			value = rabbit(value,
						   localization_path, 
						   raise_on_not_found=raise_on_not_found, 
						   _error_message="[path] ([error], debug mode ON)" if debug else "[path]")

			results[locale] = assign_variables(value, locale, **variables)
			
		return results
	
def fnum(num: float | int, locale: str = "en", ordinal: bool = False) -> str:
	if isinstance(num, float):
		num = round(num, 3)
		if locale in ("ru", "uk"):
			fmtd = '{: ,}'.format(num)
		else:
			fmtd = '{:,.3f}'.format(num)
	else:
		if locale in ("ru", "uk"):
			fmtd = '{: }'.format(num)
		else:
			fmtd = '{:,}'.format(num)
	
	if ordinal and isinstance(num, int) and locale not in ("ru", "uk"):
		fmtd += english_ordinal_for(num)
	
	return fmtd


def ftime(duration: timedelta | float, locale: str = "en-#", bold: bool = True, format: Literal['narrow', 'short', 'medium', 'long'] ="short", max_units: int = 69, **kwargs) -> str:
	if locale == "en-#":
		locale = "en"
		
	locale = Locale.parse(locale, sep="-")

	if isinstance(duration, (int, float)):
		duration = timedelta(seconds=duration)
	
	formatted = format_timespan(duration, max_units=max_units).replace(" and", ",")

	def translate_unit(component: str) -> str:
		amount, unit = component.split(" ", 1)
		
		if not unit.endswith('s'):
			unit += "s"
			
		amount = float(amount)
		if unit == "years":
			unit = "weeks"
			amount *= 52.1429
			
		translated_component = format_timedelta(timedelta(**{unit: amount}), locale=locale, format=format, **kwargs)
		return translated_component

	translated = ", ".join([translate_unit(part) for part in formatted.split(", ")])

	if bold:
		translated = re.sub(r'(\d+)', r'**\1**', translated)
	return translated

def english_ordinal_for(n: int | float):
	if isinstance(n, float):
		n = str(n).split('.')[1][0]

	if 10 <= int(n) % 100 <= 20:
		suffix = 'th'
	else:
		suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(int(n) % 10, 'th')
	
	return suffix

def assign_variables(input: Union[str, list, dict], locale: str = get_config("localization.main-locale"), **variables: dict[str, any]):
	if isinstance(input, str):
		result = input
		for name, data in {**variables, **emoji_dict}.items():
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