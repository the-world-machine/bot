from genericpath import exists
from typing import Union
from yaml import safe_load
import io
from utilities.emojis import emojis
from dataclasses import dataclass

languages = {}

@dataclass
class Localization:
    locale: str
    
    def l(self, localization_path: str, **variables: str) -> Union[str, list[str], dict]:

        
        locale = self.locale
        
        if '-' in locale:
            l_prefix = locale.split('-')[0] # Create prefix for locale, for example en_UK and en_US becomes en.

            if locale.startswith(l_prefix):
                locale = l_prefix + '-#'

        parsed_path = localization_path.split('.')

        value = fetch_language(locale)
        # Get the values for the specified category and value
        for path in parsed_path:
            
            try:
                value = value[path]
            except:
                return f'`{localization_path}` is not a valid localization path.'
        
        result = value
        
        if type(result) == dict or type(result) == list:
            return result
        else:
            return assign_variables(result, locale, **variables)
            
def fetch_language(locale: str):
    if exists(f'bot/localization/locales/{locale}.yaml'):
        with open(f'bot/localization/locales/{locale}.yaml', 'r', encoding='utf-8') as f:
            return safe_load(f)
    else:
        with open(f'bot/localization/locales/en-#.yaml', 'r', encoding='utf-8') as f:
            return safe_load(f)
    
def assign_variables(result: str, locale: str, **variables: str):
    
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