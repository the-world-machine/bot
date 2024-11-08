from genericpath import exists
import re
from typing import Literal, Union
from yaml import safe_load
from data.emojis import emojis, flatten_emojis
from dataclasses import dataclass
from datetime import timedelta
from humanfriendly import format_timespan
from babel import Locale
from babel.dates import format_timedelta
import os
from pathlib import Path
f_emojis = flatten_emojis(emojis)
emoji_dict = {f'emoji:{name.replace("icon_", "")}': f_emojis[name] for name in f_emojis}

@dataclass
class Localization:
    locale: str
    _locales = {}
    _last_modified = {}
    

    def l(self, localization_path: str, locale: str | None = None, **variables: dict[str, any]) -> Union[str, list[str], dict]:
        if locale == None:
            locale = self.locale

        return self.sl(localization_path=localization_path, locale=locale, **variables)
    
    @staticmethod
    def sl(localization_path: str, locale: str, **variables: dict[str, any]) -> Union[str, list[str], dict]:
        """ Static version of .l for single use (where making another Localization() makes it cluttery)"""
        if locale == None:
            raise ValueError("No locale provided")

        if '-' in locale:
            l_prefix = locale.split('-')[0]
            if locale.startswith(l_prefix):
                locale = l_prefix + '-#'


        got_value = False
        attempts = 0
        value = Localization.fetch_language(locale)

        value = Localization.rabbit(value, localization_path)
        
        return Localization.assign_variables(value, locale, **variables)

    @staticmethod
    def l_all(localization_path: str, **variables: str) -> dict[str, Union[str, list[str], dict]]:
        results = {}
        
        for locale in Localization.locales_list():
            value = Localization.fetch_language(locale)

            value = Localization.rabbit(value, localization_path, Localization.fetch_language("en-#"))

            results[locale] = Localization.assign_variables(value, locale, **variables)
            
        return results

    
    @staticmethod
    def locales_list() -> list[str]:
        locale_dir = Path('bot/data/locales')
        locales = []

        for file in locale_dir.glob('*.yml'):
            locale_name = file.stem
            locales.append(locale_name)

        return locales
    
    @staticmethod
    def fetch_language(locale: str):
        if locale in Localization._locales and os.path.getmtime(f'bot/data/locales/{locale}.yml') == Localization._last_modified.get(locale):
            return Localization._locales[locale]

        if exists(f'bot/data/locales/{locale}.yml'):
            with open(f'bot/data/locales/{locale}.yml', 'r', encoding='utf-8') as f:
                data = safe_load(f)
                Localization._locales[locale] = data
                Localization._last_modified[locale] = os.path.getmtime(f'bot/data/locales/{locale}.yml')
                return data
        else:
            with open(f'bot/data/locales/en-#.yml', 'r', encoding='utf-8') as f:
                data = safe_load(f)
                Localization._locales[locale] = data
                Localization._last_modified[locale] = os.path.getmtime(f'bot/data/locales/en-#.yml')
                return data
            
    @staticmethod
    def rabbit(value: dict, raw_path: str, fallback_value: dict = None, full_path = None) -> Union[str, list, dict]:
        # probably too much code? it works for now..
        if not full_path:
            full_path = raw_path
        if not raw_path:
            return value
        parsed_path: list[str] = raw_path.split('.')
        went_through: list[str] = []
        for path in parsed_path:
            got_value = False
            attempts = 0
            while not got_value:
                try:
                    if isinstance(value, dict):
                        value = Localization.rabbit(value[path], '.'.join(parsed_path[len(went_through)+1:]), fallback_value, full_path)
                    got_value = True
                except KeyError as e:
                    print(e)
                    attempts += 1
                    got_value = False

                    if attempts > 5:
                        return f'Rabitting `{full_path}` 404'
                went_through.append(path)
            return value
    
    @staticmethod
    def assign_variables(input: Union[str, list, dict], locale: str, **variables: dict[str, any]):
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
                processed.append(Localization.assign_variables(elem, locale, **variables))
            return processed
        elif isinstance(input, dict):
            for key, value in input.items():
                input[key] = Localization.assign_variables(value, locale, **variables)
            return input    
def fnum(num: float | int, locale: str = "en-#") -> str:
    if isinstance(num, float):
        fmtd = f'{num:,.3f}'
    else:
        fmtd = f'{num:,}'

    if locale in ("ru", "uk"):
        return fmtd.replace(",", " ").replace(".", ",")
    else:
        return fmtd

def ftime(duration: timedelta | float, locale: str = "en-#", bold: bool = True, format: Literal['narrow', 'short', 'medium', 'long'] ="short", **kwargs) -> str:
    if locale == "en-#":
        locale = "en"
        
    locale = Locale.parse(locale, sep="-")

    if isinstance(duration, (int, float)):
        duration = timedelta(seconds=duration)
    
    formatted = format_timespan(duration.total_seconds()).replace(" and", ",")

    def translate_unit(component: str) -> str:
        
        print(component)
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