from interactions import *
from utilities.config import get_config
from modules.textbox import TextboxModule
from utilities.misc import set_random_avatar
from utilities.profile.main import load_badges
from utilities.module_loader import load_modules
from database import ServerData, create_connection
from utilities.loc_commands import execute_loc_command
from utilities.dev_commands import execute_dev_command
import interactions.ext.prefixed_commands as prefixed_commands
from interactions.api.events import MemberAdd, Ready, MessageCreate

print('\n─ Starting The World Machine... 1/4')
intents = Intents.DEFAULT | Intents.MESSAGE_CONTENT | Intents.MESSAGES | Intents.GUILD_MEMBERS | Intents.GUILDS

client = AutoShardedClient(
    intents=intents,
    disable_dm_commands=True,
    send_command_tracebacks=False,
    send_not_ready_messages=True,
    activity=Activity(name="activity", type=ActivityType.CUSTOM, state=get_config("status", ignore_None=True))
)

prefixed_commands.setup(client, default_prefix='*')

print("\n─ Loading Commands... ─ ─ ─ ─ ─ 2/4")

load_modules(client)

print("\n─ Finalizing... ─ ─ ─ ─ ─ ─ ─ ─ 3/4")
create_connection()

print('Database Connected')
@listen(Ready)
async def on_ready():
    await load_badges()

    if get_config('do-avatar-rolling', ignore_None=True): 
        print("Rolling avatar", end=" ... ")
        if client.user.id == int(get_config('bot-id')):
            used = await set_random_avatar(client)
            print(f"used {used}")
        else:
            try:
                await client.user.edit(avatar=File('bot/images/unstable.png'))
                print("used unstable")
            except:
                print("failure")
                pass

    print("\n\n─ The World Machine is ready! ─ 4/4\n\n")

@listen(MemberAdd)
async def on_guild_join(event: MemberAdd):
    if client.user.id != int(get_config('bot-id')):
        return
    
    if event.member.bot:
        return
    
    # Check to see if we should generate a welcome message
    server_data: ServerData = await ServerData(event.guild_id).fetch()
    
    if not server_data.welcome_message:
        return

    # Generate welcome textbox.
    await TextboxModule.generate_welcome_message(event.guild, event.member, server_data.welcome_message)
    
@listen(MessageCreate)
async def on_message_create(event: MessageCreate):
    await execute_dev_command(event.message)

@listen(MessageCreate)
async def on_message_create(event: MessageCreate):
    await execute_loc_command(event.message)

client.start(get_config('token'))