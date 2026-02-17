import asyncio
from traceback import print_exc
from typing import Any
from interactions import BaseContext, User
from pyicumessageformat import Parser

from utilities.config import get_token
from utilities.emojis import flatten_emojis, on_emojis_update, emojis
from utilities.localization.formatting import fnum
from utilities.misc import decode_base64_padded
emoji_dict = {}


def edicted(emojis):
	global emoji_dict
	f_emojis = flatten_emojis(emojis)
	emoji_dict = { name.replace("icons.", "").replace("_", " "): f_emojis[name] for name in f_emojis }

edicted(emojis)
on_emojis_update(edicted)

icu_parser = Parser({
    'allow_tags': False,
})


async def icu_emoji(arguments: tuple[Any, Any, Any], variables: dict[str, Any], locale: str, ctx: Any | None = None, found_var: Any | None = None):
	global emoji_dict
	prop = arguments[0]
	if not prop:
		raise ValueError("no emoji name passed")
	if prop not in emoji_dict:
		raise ValueError(f"unknown emoji '{prop}'")

	return emoji_dict[prop]



bot_id = decode_base64_padded(get_token().split('.')[0])

async def icu_user(arguments: tuple[Any, Any, Any], variables: dict[str, Any], locale: str, ctx: Any | None = None, found_var: Any | None = None):
	user_id = str(found_var) if found_var else str(arguments[0])
	if user_id.lower() in ("twm", "the world machine", "theworldmachine", "the-world-machine"):
		user_id = bot_id
	prop = arguments[2]
	if user_id != str(bot_id):
		if not ctx or not isinstance(ctx, BaseContext):
			return ValueError("function unsupported")
		try:
			user = await ctx.bot.fetch_user(user_id)
		except Exception as e:
			user = e
		if not isinstance(user, User):
			return f"could not fetch user from userid, '{user}'"
	if user:
		user_data = {
			'mention': f"<@{user.id}>",
			'id': str(user.id),
			'username': user.username,
		}
	elif user_id == str(bot_id):
		user_data = {
			'id': bot_id,
			'mention': f"<@{bot_id}>",
			'username': "The World Machine"
		}
	else:
		return Exception("all ways of getting the user have failed and the doom has come")
	if prop not in user_data:
		raise ValueError(f"property '{prop}' not found in user ({user_data['username']}, {user_data['id']}) data")

	return user_data[prop]


async def icu_slash(arguments: tuple[Any, Any, Any], variables: dict[str, Any], locale: str, ctx: Any | None = None, found_var: Any | None = None):
	command_name = arguments[0]
	if ctx and hasattr(ctx, "client") and hasattr(ctx.client, "_interaction_lookup"):
		command = ctx.client._interaction_lookup.get(command_name)
		if command:
			return command.mention()
	return f"</{command_name}:0>"


async def icu_pretty_num(arguments: tuple[Any, Any, Any], variables: dict[str, Any], locale: str, ctx: Any | None = None, found_var: Any | None = None):
	input = str(found_var) if found_var else arguments[0]
	if isinstance(input, (int, float)):
		return fnum(input, locale)


async def icu_fallback(arguments: tuple[Any, Any, Any], variables: dict[str, Any], locale: str,  ctx: Any | None = None, found_var: Any | None = None):
	return f"{{{arguments[0]}{" " if not arguments[1] else ', '+arguments[1]}{" " if not arguments[2] else ', '+arguments[2]}}}"


icu_formatters = {
    'emoji': icu_emoji,
    'user': icu_user,
    'command': icu_slash,
    'pretty num': icu_pretty_num
}


async def parse_node(node: dict, variables, locale, ctx: Any | None = None):
	variable = node.get("name")
	if variable is None:
		return Exception("no variable passed")
	format_type = node.get("type")
	extra_format_arguments = node.get("format")
	if variable.startswith("/"):
		command_name = variable[1:]
		format_type = "command"
	if isinstance(variable, str) and '{' in variable and '}' in variable:
		variable = await render_icu(variable, variables, locale, ctx)

	if isinstance(format_type, str) and '{' in format_type and '}' in format_type:
		format_type = await render_icu(format_type, variables, locale, ctx)

	try:
		found_var = variables[variable]
	except KeyError as e:
		found_var = variable

	if not format_type and not extra_format_arguments:
		return found_var

	if format_type in icu_formatters:
		try:
			fn = icu_formatters[format_type]
			return await fn((variable, format_type, extra_format_arguments), variables, locale, ctx, found_var=found_var)
		except Exception as e:
			print_exc()
			errname = type(e).__name__
			if errname == "Exception":
				errname = "err"
			return Exception(f"{errname}: {e}")
	else:
		if variable in variables:
			return found_var
		else:
			return await icu_fallback((variable, format_type, extra_format_arguments), variables, locale, ctx, found_var=found_var)


async def render_icu(message, variables, locale, ctx: Any | None = None):
	tree = icu_parser.parse(message)
	print(tree)
	variables = { **variables, "_locale": locale}
	output = []
	for node in tree:
		parsed_node = None

		if isinstance(node, str):
			parsed_node = node
		elif isinstance(node, dict):
			parsed_node = await parse_node(node, variables, locale, ctx)
		else:
			parsed_node = Exception(f"node {node} has unexpected type for an icu tree")
		if not isinstance(parsed_node, (str, int, float)):
			parsed_node = f"<! {str(parsed_node)} !>"
		elif isinstance(parsed_node, (int, float)):
			parsed_node = str(parsed_node)
		output.append(parsed_node)

	return "".join(output)
