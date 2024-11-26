print("\033[999B", end="", flush=True)
print("\n─ Starting The World Machine... 1/4")
from utilities.config import get_config, get_token, on_prod  # order matters

from interactions import *
from modules.textbox import TextboxModule
from utilities.misc import set_status
from utilities.profile.main import load_profile_assets
from utilities.module_loader import load_modules
from utilities.loc_commands import execute_loc_command
from utilities.dev_commands import execute_dev_command
from utilities.rolling import roll_status, roll_avatar
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


if do_rolling := get_config("bot.rolling.avatar") or get_config("bot.rolling.status"):
    @Task.create(IntervalTrigger(get_config("bot.rolling.interval")))
    async def roll():
        if get_config("bot.rolling.status") == True:
            await roll_status(client)
        if get_config("bot.rolling.avatar") == True:
            await roll_avatar(client)


@listen(Ready)
async def on_ready():
    print(f"─ Logged in as {client.user.tag} ({client.user.id})")
    await set_status(client, "Loading...")
    print("\n─ Finalizing... ─ ─ ─ ─ ─ 3/4")

    load_modules(client)
    await connect_to_db()
    await load_profile_assets()

    if do_rolling:
        await roll()
        roll.start()
        
    await client._cache_interactions()
    print("\n\n─ The World Machine is ready! ─ 4/4\n\n")


@listen(MemberAdd)
async def on_guild_join(event: MemberAdd):
    if not on_prod:
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
