# import asyncio
async def TEMP():
    ...
#asyncio.run(TEMP())
print("\033[999B", end="", flush=True)
print("\n─ Starting The World Machine... 1/4")
from utilities.config import get_config, get_token # import config first (for prerequisites) 

from interactions import *
from utilities.misc import set_status
from utilities.extension_loader import load_extensions
from utilities.database.main import connect_to_db
from utilities.profile.main import load_profile_assets
from utilities.rolling import roll_status, roll_avatar
from interactions.api.events import Ready


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


@listen(Ready, delay_until_ready=True)
async def on_ready():
    print(f"─ Logged in as {client.user.tag} ({client.user.id})")
    await set_status(client, "Loading...")
    print("\n─ Finalizing... ─ ─ ─ ─ ─ 3/4")
    load_extensions(client)
    await connect_to_db()
    await load_profile_assets()
    
    if do_rolling:
        await roll()
        roll.start()
        
    await client._cache_interactions()
    print("\n\n─ The World Machine is ready! ─ 4/4\n\n")


print("\n─ Logging in... ─ ─ ─ ─ ─ ─ ─ ─ 2/4")
client.start(get_token())
