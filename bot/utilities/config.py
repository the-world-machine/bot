import yaml
from pathlib import Path
from termcolor import colored
from utilities.misc import get_current_branch, rabbit

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


cl = get_config("config-check-level", ignore_None=True)
if cl is not None:
	to_check: list[tuple[str, bool]] = [
	                                      #   (key,                       required)
	    ("bot.token", True),
	    ("database.uri", True),
	    ("dev.guild.id", True),
	    ("bot.prod.token", True),
	    ("bot.rolling.avatar", False),
	    ("bot.rolling.status", False),
	    ("bot.rolling.interval", False),
	    ("music.spotify.secret", False),
	    ("music.spotify.id", False),
	]
	for key, required in to_check:
		got = get_config(key, return_None=True, raise_on_not_found=False)
		if got != None:
			continue
		if required:
			print(colored("─ config key ") + colored(key, 'cyan') + colored(" is required", 'red'))
			if cl <= 1:
				exit(1)
		else:
			if cl <= 3:
				print(colored("─ config key ") + colored(key, 'cyan') + colored(" is missing", 'yellow'))
			if cl <= 2:
				exit(1)
on_prod = get_current_branch() == get_config("bot.prod.branch", ignore_None=True)
if get_config("bot.prod.override", ignore_None=True):
	on_prod = True
if get_config("bot.prod.token", ignore_None=True) is None:
	on_prod = False
debug = not on_prod                   # 🔥✍️
debug_override = get_config("bot.debug", ignore_None=True)


def debugging():
	return debug_override if debug_override is not None else debug


def setd(value: bool):
	global debug_override
	debug_override = value


def get_token():
	return get_config("bot.prod.token") if on_prod else get_config("bot.token")
