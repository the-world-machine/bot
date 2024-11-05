from genericpath import exists
import re
from typing import Literal, Union
from yaml import safe_load
from data.emojis import emojis
from dataclasses import dataclass
from datetime import timedelta
from humanfriendly import format_timespan
from babel import Locale
from babel.dates import format_timedelta
import os

languages = {}

import os
from pathlib import Path

@dataclass
class Localization:
    locale: str
    _locales = {}
    _last_modified = {}

    def l(self, localization_path: str, guild_locale: str | None = None, **variables: str) -> Union[str, list[str], dict]:
        locale = guild_locale if guild_locale else self.locale
        
        if '-' in locale:
            l_prefix = locale.split('-')[0]  # Create prefix for locale, e.g., en_UK and en_US becomes en.
            if locale.startswith(l_prefix):
                locale = l_prefix + '-#'

        parsed_path = localization_path.split('.')

        got_value = False
        attempts = 0
        
        while not got_value:
            value = self.fetch_language(locale)

            # Get the values for the specified category and value
            for path in parsed_path:
                try:
                    value = value[path]
                    got_value = True
                except KeyError:  # Be specific about the error type
                    attempts += 1
                    locale = 'en-#'
                    got_value = False

                    if attempts > 5:
                        return f'`{localization_path}`'
        
        result = value
        
        if isinstance(result, (dict, list)):
            return result
        else:
            return self.assign_variables(result, locale, **variables)

    def l_all(self, localization_path: str, locale_override: str = None, **variables: str) -> dict[str, Union[str, list[str], dict]]:
        results = {}
        
        available_locales = self.locales_list()
        
        if locale_override:
            available_locales = [locale_override]

        for locale in available_locales:
            try:
                value = self.fetch_language(locale)
                parsed_path = localization_path.split('.')

                for path in parsed_path:
                    value = value[path]

                results[locale] = self.assign_variables(value, locale, **variables)
            except (KeyError, FileNotFoundError):
                results[locale] = f'`{localization_path}` not found'

        return results

    def locales_list(self) -> list[str]:
        locale_dir = Path('bot/data/locales')
        locales = []

        for file in locale_dir.glob('*.yaml'):
            locale_name = file.stem
            locales.append(locale_name)

        return locales

    def fetch_language(self, locale: str):
        if locale in self._locales and os.path.getmtime(f'bot/data/locales/{locale}.yml') == self._last_modified.get(locale):
            return self._locales[locale]

        if exists(f'bot/data/locales/{locale}.yaml'):
            with open(f'bot/data/locales/{locale}.yaml', 'r', encoding='utf-8') as f:
                data = safe_load(f)
                self._locales[locale] = data
                self._last_modified[locale] = os.path.getmtime(f'bot/data/locales/{locale}.yml')
                return data
        else:
            with open(f'bot/data/locales/en-#.yaml', 'r', encoding='utf-8') as f:
                data = safe_load(f)
                self._locales[locale] = data
                self._last_modified[locale] = os.path.getmtime(f'bot/data/locales/en-#.yml')
                return data

    def assign_variables(self, result: str, locale: str, **variables: str):
        emoji_dict = {f'emoji:{name.replace("icon_", "")}': emojis[name] for name in emojis.keys()}
        
        for name, data in {**variables, **emoji_dict}.items():
            if isinstance(data, (int, float)):
                data = fnum(data, locale)
            elif not isinstance(data, str):
                data = str(data)

            result = result.replace(f'[{name}]', data)
        
        return result
    
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