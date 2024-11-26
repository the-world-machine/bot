import io
import re
import sys
import time
import json
from yaml import dump
from aioconsole import aexec
from termcolor import colored
from utilities.emojis import emojis
import utilities.database.main as main
from utilities.localization import fnum
from interactions import Embed, Message
from asyncio import iscoroutinefunction
from utilities.config import get_config, on_prod
from utilities.message_decorations import Colors
from utilities.module_loader import load_modules # used, actually
from traceback import _parse_value_tb, TracebackException
from utilities.shop.fetch_shop_data import reset_shop_data

ansi_escape_pattern = re.compile(r'\033\[[0-9;]*[A-Za-z]')

async def get_collection(collection: str, _id: str):
    key_to_collection: dict[str, main.Collection] = {
        'user': main.UserData(_id),
        'nikogotchi': main.Nikogotchi(_id),
        'nikogotchi_old': main.NikogotchiData(_id),
        'server': main.ServerData(_id)
    }
    
    return key_to_collection[collection]


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
    if not message.content:
        return
    
    if message.author.bot and str(message.author.id) not in get_config('dev.whitelist'):
        return
    
    if str(message.author.id) not in get_config('dev.whitelist'):
        return
    
    prefix = command_marker.split('.')
    
    if not (message.content[0] == prefix[0] and message.content[-1] == prefix[1]):
        return
    
    command_content = message.content[1:-1].strip()
    
    args = command_content.split(" ")
    
    subcommand_name = args[0]

    match subcommand_name:
        case "bot":
            action = args[1]
            match action:
                case "refresh":
                    try:
                        module = args[2]
                    except IndexError as e:
                        return await message.reply('[ Specify a module to refresh, or "all" ]')
                    if module == "all":
                        message.content = "{eval ```py\nload_modules(message.client, unload=True, print=print)\n```}"
                        return await execute_dev_command(message)
                    else:
                        msg = await message.reply(f"[ Reloading module... {emojis['icons']['loading']} ]")
                        msg.client.reload_extension(module)
                        return await msg.edit(content=f"[ Reloaded {module} ]")
                case "sync_commands":
                    msg = await message.reply(f"[ Synchronizing commands... {emojis['icons']['loading']} ]")
                    await msg.client.synchronise_interactions()
                    return await msg.edit(content=f"[ Synchronized ]")
                case _:
                    return await message.reply("Available subcommands: `refresh` / `sync_commands`")
        case "eval":
            code = command_content.split(f"eval ")
            referenced_message = message.get_referenced_message();
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
            state = {
                'asnyc_warn': False,
                'strip_ansi_sequences': True,
                'raisure': False
            }
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
            except:
                end_time = time.perf_counter()
                state['raisure'] = True
                exc_type, exc_value, exc_tb = sys.exc_info()

                if str(exc_value) in ("py codeblock is required here", "no code provided"):
                    result = str(exc_value)
                if method == "eval":
                    result = str(exc_value)
                else:
                    value, tb = _parse_value_tb(exc_type, exc_value, exc_tb)
                    tb = TracebackException(type(value), value, tb, limit=None, compact=True)
                    lines = []
                    for line in tb.format(chain=True):
                        lines.append(line
                                    .replace('  File "<aexec>", ', " - at ")
                                    .replace('  File "<string>", ', " - at ")
                                    .replace(', in __corofn','')
                                    .replace(', in <module>',''))
                    lines.pop(0)
                    result =  ''.join(lines)
                    result_tmp = result.split(" in redir_prints\n    method(code, globals, locals)")
                    if len(result_tmp) != 2: # aexec
                        state['asnyc_warn'] = True
                        result_tmp = result.split(" new_local = await coro\n                        ^^^^^^^^^^\n")
                    result = result_tmp[1] if len(result_tmp) > 1 else result

            runtime = (end_time - start_time) * 1000
            
            async def handle_reply(runtime, result, note=""):
                desc = f"-# Runtime: {fnum(runtime)} ms{note}"
                if state['asnyc_warn']:
                    desc+="\n-# All line numbers are offset by +1 cuz of await"
                if result == None and method in ("aexec", "exec"):
                    desc+="\n-# Nothing was printed"
                else:
                    desc+=f"\n```py\n{str(result).replace('```', '` ``')}```"
                color = Colors.DEFAULT
                if state['raisure']:
                    color = Colors.BAD
                return await message.reply(
                    embeds=Embed(
                        color=color,
                        description=desc
                    ))
            try:
                if isinstance(result, str) and state['strip_ansi_sequences']:
                    result = ansi_escape_pattern.sub('', result)
                return await handle_reply(runtime, result)
            except Exception as e:
                if "Description cannot exceed 4096 characters" in str(e): # TODO: paging
                    return await handle_reply(runtime, result[0:3900], "\n-# Result too long to display, showing first 3900 characters") 
                else:
                    result = f"Raised an exception when replying(WHAT did you do): {str(e)}"
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    value, tb = _parse_value_tb(exc_type, exc_value, exc_tb)
                    tb = TracebackException(type(value), value, tb, limit=None, compact=True)
                    lines = []
                    for line in tb.format(chain=True):
                        lines.append(line)
                    lines.pop(0)
                    result =  ''.join(lines)
                    return await handle_reply(runtime, result)
        case "shop":
            items = await main.fetch_items()
            shop = items['shop']

            match args[1]:
                case "view":
                    return await message.reply(f"```yml\n{dump(shop)}```")
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

                        collection = await main.fetch_from_database(await get_collection(collection, _id))
                        
                        await collection.update(**data)
                        
                        return await message.reply(
                            '`[ Successfully updated ]`'
                        )
                    case "view":
                        collection = args[2]
                        _id = args[3]
                        value = args[4]
                        
                        if collection == 'shop':
                            collection = await get_collection(collection, 0)
                        else:
                            collection = await main.fetch_from_database(await get_collection(collection, _id))
                        
                        return await message.reply(
                            f'`[ The value of {value} is {str(collection.__dict__[value])} ]`'
                        )
                    case "view_all":
                        collection = args[2]
                        _id = args[3]
                        
                        collection = await main.fetch_from_database(await get_collection(collection, _id))
                        
                        data = collection.__dict__
                        
                        return await message.reply(f"```yml\n{dump(data)}```")
                    case "wool":
                        _id = args[2]
                        amount = int(args[3])
                        
                        collection: main.UserData = await main.fetch_from_database(await get_collection('user', _id))
                        
                        await collection.manage_wool(amount)
                        
                        return await message.reply(
                            f'`[ Successfully modified wool, updated value is now {collection.wool} ]`'
                        )
                    case _:
                        return await message.reply("Available subcommands: `set` / `view` / `view_all` / `wool`")
            except Exception as e:
                await message.reply(
                    f'`[ Error with command ({e}) ]`'
                )
        case "locale_override":
            return
        case _:
            await message.reply("Available commands: `eval` / `shop` / `db` / `bot`. See source code for usage")
    formatted_command_content = command_content.replace('\n', '\n'+colored('│ ', 'yellow'))
    if subcommand_name == "db":
        subcommand_name += " ─"
    
    print(f"{colored('┌ dev_commands', 'yellow')} ─ ─ ─ ─ ─ ─ ─ ─ {subcommand_name}\n"+
          f"{colored('│', 'yellow')} {message.author.mention} ({message.author.username}) ran:\n"+
          f"{colored('│', 'yellow')} {formatted_command_content}\n"+
          f"{colored('└', 'yellow')} ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─")
