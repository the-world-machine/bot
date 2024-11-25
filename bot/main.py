print("\n─ Starting The World Machine... 1/4")
from utilities.config import get_config, get_token  # order matters

from interactions import *
from modules.textbox import TextboxModule
from utilities.profile.main import load_profile_assets
from utilities.module_loader import load_modules
from utilities.loc_commands import execute_loc_command
from utilities.dev_commands import execute_dev_command
from utilities.misc import set_random_avatar, set_status
from utilities.database.main import ServerData, connect_to_db
from interactions.api.events import MemberAdd, Ready, MessageCreate


intents = (
    Intents.DEFAULT
    | Intents.MESSAGE_CONTENT
    | Intents.MESSAGES
    | Intents.GUILD_MEMBERS
    | Intents.GUILDS
)

client = AutoShardedClient(
    intents=intents,
    disable_dm_commands=True,
    send_command_tracebacks=False,
    send_not_ready_messages=True,
    sync_interactions=False,
    sync_ext=False
)

statuses = get_config("bot.status", ignore_None=True)
if statuses != None:

    @Task.create(IntervalTrigger(get_config("bot.roll-interval")))
    async def roll_status(override: str = None):
        return await set_status(client, statuses)


@listen(Ready)
async def on_ready():
    print(f"─ Logged in as {client.user.tag} ({client.user.id})")
    await set_status(client, "Loading...")
    print("\n─ Finalizing... ─ ─ ─ ─ ─ 3/4")

    load_modules(client)
    await connect_to_db()
    await load_profile_assets()

    if statuses != None:
        await roll_status()
        roll_status.start()
    if get_config("bot.avatar-rolling", ignore_None=True):
        print("Rolling avatar", end=" ... ")
        if client.user.id == int(get_config("bot.main-id")):
            used = await set_random_avatar(client)
            print(f"used {used}")
        else:
            try:
                await client.user.edit(avatar=File("bot/images/unstable.png"))
                print("used unstable")
            except:
                print("failure")
                pass

    print("\n\n─ The World Machine is ready! ─ 4/4\n\n")


@listen(MemberAdd)
async def on_guild_join(event: MemberAdd):
    if str(client.user.id) != str(get_config("bot.main-id")):
        return

    if event.member.bot:
        return

    # Check to see if we should generate a welcome message
    server_data: ServerData = await ServerData(event.guild_id).fetch()

    if not server_data.welcome_message:
        return

    # Generate welcome textbox.
    await TextboxModule.generate_welcome_message(
        event.guild, event.member, server_data.welcome_message
    )


@listen(MessageCreate)
async def on_message_create(event: MessageCreate):
    res = await execute_dev_command(event.message)
    if not res:
        await execute_loc_command(event.message)


print("\n─ Logging in... ─ ─ ─ ─ ─ ─ ─ ─ 2/4")
client.start(get_token())
