import io
import re
import sys
import time
import json
import yaml
import traceback as tb
from aioconsole import aexec
from termcolor import colored
from utilities.misc import shell
from utilities.emojis import emojis
import utilities.database.main as main
from utilities.localization import fnum
from interactions import Embed, Message
from asyncio import iscoroutinefunction
import utilities.database.schemas as schemas
from utilities.config import get_config, on_prod
from utilities.message_decorations import Colors
from utilities.extensions import load_commands  # used, actually
from utilities.shop.fetch_shop_data import reset_shop_data

ansi_escape_pattern = re.compile(r'\033\[[0-9;]*[A-Za-z]')


def get_collection(collection: str, _id: str):
	return getattr(schemas, collection)(_id)


class CapturePrints:

	def __init__(self, output_buffer):
		self.output_buffer = output_buffer
		self.bogos_printed = False
		self.print = self._capture_print

	def __enter__(self):
		return self

	def _capture_print(self, *args, sep=' ', end='\n', file=None, flush=False):
		self.bogos_printed = True
		output = sep.join(map(str, args))
		self.output_buffer.write(output + end)

		if flush and file is not None:
			file.flush()

	def __exit__(self, exc_type, exc_val, exc_tb):
		pass


async def redir_prints(method, code, locals=None, globals=None):
	if locals is None:
		locals = {}
	output_buffer = io.StringIO()
	with CapturePrints(output_buffer) as cp:
		locals['print'] = cp.print

		if iscoroutinefunction(method):
			await method(code, locals)
		else:
			method(code, globals, locals)
	if cp.bogos_printed:
		return cp.output_buffer.getvalue()


command_marker = get_config('dev.command-marker')
if on_prod:
	_pm = get_config("bot.prod.command-marker", ignore_None=True)
	command_marker = _pm if _pm is not None else command_marker


async def execute_dev_command(message: Message):
	try:
		return await _execute_dev_command(message)
	except Exception as e:
		result = f"Raised an exception when processing command: {str(e)}"
		lines = []
		raw_tb = tb.format_exc(chain=True)
		print(raw_tb)
		for line in raw_tb.split("\n"):
			lines.append(line)
		lines.pop(0)
		result = '\n'.join(lines)
		return await message.reply(
		    embeds=Embed(color=Colors.BAD, description=f"\n```py\n{result[0:3900].replace('```', '` ``')}```")
		)


async def _execute_dev_command(message: Message):
	if not message.content:
		return

	if message.author.bot and str(message.author.id) not in get_config('dev.whitelist', as_str=False):
		return

	if str(message.author.id) not in get_config('dev.whitelist', as_str=False):
		return

	prefix = command_marker.split('.')

	if not (message.content[0] == prefix[0] and message.content[-1] == prefix[1]):
		return

	command_content = message.content[1:-1].strip()

	args = command_content.split(" ")

	subcommand_name = args[0]

	formatted_command_content = command_content.replace('\n', '\n' + colored('│ ', 'yellow'))
	print(
	    f"{colored('┌ dev_commands', 'yellow')} ─ ─ ─ ─ ─ ─ ─ ─ {subcommand_name + (" ─" if subcommand_name=="db" else "")}\n" +
	    f"{colored('│', 'yellow')} {message.author.mention} ({message.author.username}) ran:\n" +
	    f"{colored('│', 'yellow')} {formatted_command_content}\n" +
	    f"{colored('└', 'yellow')} ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"
	)

	match subcommand_name:
		case "bot":
			action = args[1]
			match action:
				case "refresh":
					try:
						extension = args[2]
					except IndexError as e:
						return await message.reply('[ Specify an extension to refresh, or "all" ]')
					if extension == "all":
						message.content = "{eval ```py\nload_commands(message.client, unload=True, print=print)\n```}"
						return await execute_dev_command(message)
					else:
						msg = await message.reply(f"[ Working... {emojis['icons']['loading']} ]")
						try:
							msg.client.reload_extension(extension)
						except Exception as e:
							await message.reply(f'`[ {e} ]`')
						return await msg.edit(content=f"[ Reloaded {extension} ]")
				case "sync_commands":
					msg = await message.reply(f"[ Synchronizing commands... {emojis['icons']['loading']} ]")
					await msg.client.synchronise_interactions()
					return await msg.edit(content=f"[ Synchronized ]")
				case "shell":
					msg = await message.reply(f"[ Running... {emojis['icons']['loading']} ]")
					parse = ' '.join(args).split(args[1])
					if len(parse) < 1:
						return await msg.edit(content=f"[ No command passed ]")
					output = shell(parse[1])
					return await msg.edit(content=f"[ Done ]\n```bash\n{output}```")

				case _:
					return await message.reply("Available subcommands: `refresh` / `sync_commands`")
		case "eval":
			code = command_content.split(f"eval ")
			referenced_message = message.get_referenced_message()
			reply_content = referenced_message.content if referenced_message and referenced_message.content else None

			if len(code) == 1 and reply_content and reply_content.startswith("```py\n"):
				code = reply_content
			elif len(code) > 1:
				code = command_content.split("eval ")[1]
			else:
				code = ""

			if code.startswith("```py\n") and code.endswith("```"):
				code = code[5:-3].strip()
				if "await" in code:
					method = "aexec"
				else:
					method = "exec"
			else:
				method = "eval"

			result = None
			runtime = None
			start_time = time.perf_counter()
			state = { 'asnyc_warn': False, 'strip_ansi_sequences': True, 'raisure': False}
			try:
				match method:
					case "exec":
						result = await redir_prints(exec, code, locals(), globals())
					case "aexec":
						result = await redir_prints(aexec, code, locals())
					case "eval":
						if len(code) == 0:
							raise BaseException("no code provided")
						result = eval(code, globals(), locals())
				end_time = time.perf_counter()
			except Exception as e:
				end_time = time.perf_counter()
				state['raisure'] = True
				exc_type, exc_value, exc_tb = sys.exc_info()

				if str(exc_value) in ("py codeblock is required here", "no code provided"):
					result = str(exc_value)
				if method == "eval":
					result = str(exc_value)
				else:
					lines = []
					raw_tb = tb.format_exc(chain=True)
					print(raw_tb)
					for line in raw_tb.split("\n"):
						# yapf: disable
						lines.append(
						 line.replace('  File "<aexec>", ', " - at ")
						     .replace('  File "<string>", ', " - at ")
						     .replace(', in __corofn', '')
						     .replace(', in <module>', '')
						)
						# yapf: enable
					lines.pop(0)
					result = '\n'.join(lines)
					result_tmp = result.split(" in redir_prints\n    method(code, globals, locals)")
					if len(result_tmp) != 2:  # aexec
						state['asnyc_warn'] = True
						result_tmp = result.split(" new_local = await coro\n                        ^^^^^^^^^^\n")
					result = result_tmp[1] if len(result_tmp) > 1 else result

			runtime = (end_time - start_time) * 1000

			async def handle_reply(runtime, result, note=""):
				desc = f"-# Runtime: {fnum(runtime)} ms{note}"
				if state['asnyc_warn']:
					desc += "\n-# All line numbers are offset by +1 cuz of await"
				if result == None and method in ("aexec", "exec"):
					desc += "\n-# Nothing was printed"
				else:
					desc += f"\n```py\n{str(result).replace('```', '` ``')}```"
				color = Colors.DEFAULT
				if state['raisure']:
					color = Colors.BAD
				return await message.reply(embeds=Embed(color=color, description=desc))

			try:
				if isinstance(result, str) and state['strip_ansi_sequences']:
					result = ansi_escape_pattern.sub('', result)
				return await handle_reply(runtime, result)
			except Exception as e:
				print(e)
				if "Description cannot exceed 4096 characters" in str(e):  # TODO: paging
					return await handle_reply(
					    runtime,
					    str(result)[0:3900], "\n-# Result too long to display, showing first 3900 characters"
					)
				else:
					result = f"Raised an exception when replying(WHAT did you do): {str(e)}"
					lines = []
					for line in tb.format_exc(chain=True).split("\n"):
						lines.append(line)
					lines.pop(0)
					result = '\n'.join(lines)
					return await handle_reply(runtime, result)
		case "shop":
			items = await main.fetch_items()
			shop = items['shop']

			match args[1]:
				case "view":
					return await message.reply(f"```yml\n{yaml.dump(shop, default_flow_style=False, Dumper=yaml.SafeDumper)}```")
				case "reset":
					try:
						await reset_shop_data()
						return await message.reply('`[ Successfully reset shop ]`')
					except Exception as e:
						return await message.reply(f'`[ {e} ]`')
				case _:
					return await message.reply("Available subcommands: `view` / `reset`")
		case "db":
			try:
				match args[1]:
					case "set":

						pattern = r'\{(?:[^{}]*|\{[^{}]*\})*\}'

						matches = re.findall(pattern, command_content)

						collection = args[2]
						_id = args[3]
						str_data = matches[0]

						data = json.loads(str_data)

						collection = await get_collection(collection, _id).fetch()

						await collection.update(**data)

						return await message.reply('`[ Successfully updated ]`')
					case "view":
						collection = args[2]
						_id = args[3]
						value = args[4]

						if collection == 'shop':
							collection = await get_collection(collection, 0)
						else:
							collection = await get_collection(collection, _id).fetch()

						return await message.reply(f'`[ The value of {value} is {str(collection.__dict__[value])} ]`')
					case "view_all":
						collection = args[2]
						_id = args[3]

						collection = await get_collection(collection, _id).fetch()

						return await message.reply(f"```yml\n{yaml.dump(main.to_dict(collection), default_flow_style=False, Dumper=yaml.SafeDumper)}```")
					case "wool":
						_id = args[2]
						amount = int(args[3])

						collection: schemas.UserData = await schemas.UserData(_id).fetch()

						await collection.manage_wool(amount)

						return await message.reply(
						    f'`[ Successfully modified wool, updated value is now {collection.wool} ]`'
						)
					case _:
						return await message.reply("Available subcommands: `set` / `view` / `view_all` / `wool`")
			except Exception as e:
				await message.reply(f'`[ Error with command ({e}) ]`')
		case "locale_override":
			return
		case _:
			return {}
