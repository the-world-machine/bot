from datetime import date, datetime
from typing import Any, Literal, Type, TypeVar, Union, overload
from yaml import safe_load as load_yml_file
from pathlib import Path
from termcolor import colored
from utilities.misc import get_current_branch, rabbit

bcpath = Path("bot-config.yml")
try:
	with open(bcpath, 'r') as f:
		config = load_yml_file(f)
		print("Loaded configuration")
except FileNotFoundError as e:
	print(
	    colored(f"─ config file at '{bcpath.resolve()}' is missing.\nAre you sure you set it up correctly?", 'yellow')
	)
	exit(1)

C = TypeVar("C")


@overload
def get_config(path: str, *, raise_on_not_found: bool = True, ignore_None: Literal[False] = False) -> str:
	...


@overload
def get_config(path: str, *, raise_on_not_found: bool = True, ignore_None: Literal[True]) -> str | None:
	...


@overload
def get_config(
    path: str, *, typecheck: Type[C], raise_on_not_found: bool = True, ignore_None: Literal[False] = False
) -> C:
	...


@overload
def get_config(
    path: str, *, typecheck: Type[C], raise_on_not_found: bool = True, ignore_None: Literal[True]
) -> C | None:
	...


def get_config(
    path: str,
    *,
    typecheck: Type[C] | None = None,
    raise_on_not_found: bool = True,
    ignore_None: bool = False,
) -> C | str | None:
	"""
	Retrieves a value from the configuration file.

	Args:
	    path: The dot-separated path to the configuration value.
	    typecheck: The expected type of the value. If provided, the function will validate
	               the type and return it, or raise a TypeError. If omitted, the value
	               is returned as a string.
	    raise_on_not_found: If True (default), raises an error if the path is not found.
	    ignore_None: If True, suppresses errors for missing paths and returns None instead.
	                 This overrides `raise_on_not_found`.
	"""
	should_raise = raise_on_not_found and not ignore_None
	return_none = ignore_None

	res = rabbit(
	    config,
	    path,
	    raise_on_not_found=should_raise,
	    return_None_on_not_found=return_none,
	    _error_message="Configuration does not have [path]"
	)

	if res is None:
		return None

	if typecheck is None:
		return str(res)

	# Typecheck case: validate the type
	if not isinstance(res, typecheck):
		raise TypeError(
		    f"Configuration value for '{path}' has type {type(res).__name__}, "
		    f"but expected {typecheck.__name__}"
		)

	return res


# --- END: REPLACEMENT FOR get_config() ---

cl = get_config("config-check-level", typecheck=int, ignore_None=True)
if cl is not None:
	to_check: list[tuple[str, bool]] = [
	    #   (key,                       required)
	    ("bot.token", True),
	    ("database.uri", True),
	    ("localization.main-locale", True),
	    ("dev.guild.id", False),
	    ("bot.prod.token", False),
	    ("bot.rolling.avatar", False),
	    ("bot.rolling.status", False),
	    ("bot.rolling.interval", False),
	    ("music.spotify.secret", False),
	    ("music.spotify.id", False),
	]
	for key, required in to_check:
		# Calling get_config without typecheck will return str or None
		got = get_config(key, ignore_None=True)
		if got is not None:
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
if get_config("bot.prod.override", typecheck=bool, ignore_None=True):
	on_prod = True
if get_config("bot.prod.token", ignore_None=True) is None:
	on_prod = False

debug = not on_prod  # 🔥✍️
debug_override = get_config("bot.debug", typecheck=bool, ignore_None=True)


def debugging():
	return debug_override if debug_override is not None else debug


def setd(value: bool):
	global debug_override
	debug_override = value


def get_token() -> str:
	out: str | None
	if not on_prod:
		return get_config("bot.token")
	out = get_config("bot.prod.token", ignore_None=True)
	if out is None:
		out = get_config("bot.token")
	return out
