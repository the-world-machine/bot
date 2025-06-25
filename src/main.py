#import asyncio

#async def temp():

#if __name__ == "__main__":
#	asyncio.run(temp())
print("\033[999B", end="", flush=True)
print("\n─ Starting The World Machine... 1/3")
from utilities.config import get_config, get_token

from interactions import *
# from utilities.misc import set_status
from utilities.extensions import load_commands, assign_events
from utilities.database.main import connect_to_db
from utilities.profile.main import load_profile_assets
from utilities.rolling import roll_status, roll_avatar
from interactions.api.events import Startup
from datetime import datetime
from utilities.logging import createLogger

logger = createLogger(__name__)

intents = (Intents.DEFAULT | Intents.MESSAGE_CONTENT | Intents.MESSAGES | Intents.GUILD_MEMBERS | Intents.GUILDS)

client = Client(
    intents=intents,
    send_command_tracebacks=False,
    send_not_ready_messages=True,
    sync_interactions=False,
    sync_ext=False,
    logger=createLogger("client")
)
client.started_at = datetime.now()
if do_rolling := get_config("bot.rolling.avatar", as_str=False) or get_config("bot.rolling.status"):

	@Task.create(IntervalTrigger(get_config("bot.rolling.interval", as_str=False)))
	async def roll():
		if get_config("bot.rolling.status", as_str=False) == True:
			await roll_status(client)
		if get_config("bot.rolling.avatar", as_str=False) == True:
			await roll_avatar(client)


assign_events(client)


@listen(Startup)
async def on_startup(event: Startup):
	# await set_status(client, "[ Loading... ]")
	load_commands(client)
	await connect_to_db()
	await load_profile_assets()
	await client.wait_until_ready()
	await client._cache_interactions()
	if do_rolling:
		await roll()
		roll.start()
	print("\n\n─ The World Machine is ready! ─ 3/3\n\n")
	startupped = datetime.now()
	from extensions.events.Ready import ReadyEvent
	await ReadyEvent.followup(startupped)


print("\n─ Finalizing... ─ ─ ─ ─ ─ ─ ─ ─ 2/3")
client.start(get_token())
