import yaml
from pathlib import Path
from termcolor import colored
from utilities.misc import rabbit

bcpath = Path("bot-config.yml")
try:
    with open(bcpath, 'r') as f:
        config = yaml.safe_load(f)
        print("Loaded configuration")
except FileNotFoundError as e:
    print(colored(f"─ config file at '{bcpath.resolve()}' is missing.\nAre you sure you set it up correctly?", 'yellow'))
    exit(1)

def get_config(path: str, raise_on_not_found: bool | None = True, return_None: bool | None = False, ignore_None: bool = False):
    if ignore_None:
        raise_on_not_found = False
        return_None = True
    return rabbit(config, path, raise_on_not_found=raise_on_not_found, return_None_on_not_found=return_None, _error_message="Configuration does not have [path]")

what_do_i_call_this: list[tuple[str, bool]] = [
#   (key,                       required)
    ("bot.token",               True),
    ("database.uri",            True),
    ("bot.main-id",             False),
    ("music.spotify.secret",    False),
    ("music.spotify.id",        False),
]
for key, required in what_do_i_call_this:
    got = get_config(key, return_None=True, raise_on_not_found=False)
    if got != None:
        continue;
    if required:
        print(colored(f"─ config key '{colored(key, 'cyan')}' is required", 'red'))
        exit(1)
    else:
        print(colored(f"─ config key '{colored(key, 'cyan')}' is missing", 'yellow'))