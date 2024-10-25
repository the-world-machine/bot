import io
import json
import re
from interactions import Embed, Message
from localization.loc import fnum
from utilities.shop.fetch_shop_data import reset_shop_data
from config_loader import load_config
import database
from aioconsole import aexec
from termcolor import colored
import time
from asyncio import iscoroutinefunction, sleep
from traceback import _parse_value_tb, TracebackException
import sys
async def get_collection(collection: str, _id: str):
    key_to_collection: dict[str, database.Collection] = {
        'user': database.UserData(_id),
        'nikogotchi': database.Nikogotchi(_id),
        'nikogotchi_old': database.NikogotchiData(_id),
        'server': database.ServerData(_id)
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

async def execute_dev_command(message: Message):
    
    if message.author.bot:
        return
    
    if not str(message.author.id) in load_config('dev-command-user-list'):
        return
    
    if not message.content:
        return
    
    # This is not a valid command if brackets do not surround the message.
    if not (message.content[0] == '{' or message.content[-1] == '}'):
        return
    
    # Remove the brackets
    command_content = message.content[1:-1].strip()
    
    # Split the command into parts
    args = command_content.split(" ")
    
    subcommand_name = args[0]
    
    match subcommand_name:
        case "eval":
            method = args[1] if len(args) > 1 else ''
            _args = command_content.split(f"eval{method} ")
            if method.startswith("```py\n"):
                _args = command_content.split(f"eval ")
            code = _args[1] if len(_args) > 1 else ''
            if code.startswith("```py\n") and code.endswith("```"):
                code = code[5:-3].strip()
                if "await" in code:
                    method = "aexec"
                else:
                    method = "exec"
            else:
                code = command_content.split(f"eval ")[1] if len(command_content.split(f"eval ")) > 1 else ''
                method = "eval"
            

            result = None
            runtime = None
            raisure = False
            asnyc_warn = False
            start_time = time.perf_counter()
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
                raisure = True
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
                        asnyc_warn = True
                        result_tmp = result.split(" new_local = await coro\n                        ^^^^^^^^^^\n")
                    result = result_tmp[1] if len(result_tmp) > 1 else result

            runtime = (end_time - start_time) * 1000
            
            async def handle_reply(runtime, result, note=""):
                desc = f"-# Runtime: {fnum(runtime)} ms{note}"
                if asnyc_warn:
                    desc+="\n-# All line numbers are offset by +1 cuz of await"
                if result == None and method in ("aexec", "exec"):
                    desc+="\n-# Nothing was printed"
                else:
                    desc+=f"\n```py\n{str(result).replace('```', '{` ``}')}```"
                color = None
                if raisure:
                    color = 0xff0000
                await message.reply(
                    embeds=Embed(
                        color=color,
                        description=desc
                    ))
            try:
                await handle_reply(runtime, result)
            except Exception as e:
                if "Description cannot exceed 4096 characters" in str(e): # TODO: paging
                    await handle_reply(runtime, result[0:3900], "\n-# Result too long to display, showing first 3900 characters") 
                else:
                    result = f"Raised an exception when replying(what did you do): {str(e)}"
                    print("Exception while replying", e)
                    await handle_reply(runtime, result)
        case "shop":
        
            action = args[1]
            
            items = await database.fetch_items()
            shop = items['shop']
            
            if action == 'view':
                result = '```\n'
                    
                for key in shop.keys():
                    result += f'{key}: {str(shop[key])}\n'
                    
                result += '```'
                
                await message.reply(result)
            
            if action == 'reset':
                await reset_shop_data('en-US')
                
                await message.reply(
                    f'`[ Successfully reset shop. ]`'
                )
        case "db":
            try:
                action = args[1]
                
                if action == 'set':
                    
                    pattern = r'\{(?:[^{}]*|\{[^{}]*\})*\}'
                    
                    matches = re.findall(pattern, command_content)
                    
                    collection = args[2]
                    _id = args[3]
                    str_data = matches[0]

                    data = json.loads(str_data)

                    collection = await database.fetch_from_database(await get_collection(collection, _id))
                    
                    await collection.update(**data)
                    
                    await message.reply(
                        f'`[ Successfully updated value(s). ]`'
                    )
                    
                if action == 'view':
                    collection = args[2]
                    _id = args[3]
                    value = args[4]
                    
                    if collection == 'shop':
                        collection = await get_collection(collection, 0)
                    else:
                        collection = await database.fetch_from_database(await get_collection(collection, _id))
                    
                    await message.reply(
                        f'`[ The value of {value} is {str(collection.__dict__[value])}. ]`'
                    )
                    
                if action == 'view_all':
                    collection = args[2]
                    _id = args[3]
                    
                    collection = await database.fetch_from_database(await get_collection(collection, _id))
                    
                    data = collection.__dict__
                    
                    result = '```\n'
                    
                    for key in data.keys():
                        result += f'{key}: {str(data[key])}\n'
                        
                    result += '```'
                    
                    await message.reply(result)
                    
                    
                if action == 'wool':
                    _id = args[2]
                    amount = int(args[3])
                    
                    collection: database.UserData = await database.fetch_from_database(await get_collection('user', _id))
                    
                    await collection.manage_wool(amount)
                    
                    await message.reply(
                        f'`[ Successfully modified wool, updated value is now {collection.wool}. ]`'
                    )
                    
            except Exception as e:
                await message.reply(
                    f'`[ Error with command. ({e}) ]`'
                )
        case _:
            return await message.reply("Available commands: `eval` / `shop` / `db`. See source code for usage")
    formatted_command_content = command_content.replace('\n', '\n'+colored('│ ', 'yellow'))
    if subcommand_name == "db":
        subcommand_name += " ─"
    
    print(f"{colored('┌ dev_commands', 'yellow')} ─ ─ ─ ─ ─ ─ ─ ─ {subcommand_name}\n"+
          f"{colored('│', 'yellow')} {message.author.mention} ({message.author.username}) ran:\n"+
          f"{colored('│', 'yellow')} {formatted_command_content}\n"+
          f"{colored('└', 'yellow')} ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─")