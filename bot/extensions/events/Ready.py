from asyncio import sleep
from datetime import datetime, timedelta
from interactions import *
from interactions.api.events import Ready, Startup
from utilities.config import get_config
from utilities.message_decorations import Colors
from utilities.misc import get_git_hash
from utilities.emojis import emojis
# Should serve as an example event file, otherwise should've remained in main.py

stuff = { "started": False, "queue": [], "followup_at": None}


class ReadyEvent(Extension):

	def log(thing):
		print(thing, stuff['queue'])
		stuff['queue'].append(thing)
		pass

	def followup(time: datetime):
		stuff["followup_at"] = time

	@listen(Ready)
	async def ready(self, event: Ready):
		client = event.client  # <- client is always defined on `event`
		print(f"─ Logged into Discord as {client.user.tag} ({client.user.id})")

	@listen(Ready)
	async def send_logs(self, event: Ready):
		if not stuff['started']:
			stuff['started'] = True  # yapf: ignore
			# this exists to prevent sending more "ready" messages whenever discord disconnects (ready event may fire again)
		else:
			return
		client = event.client
		client.ready_at = datetime.now()
		self.ready_at = client.ready_at
		from utilities.localization import fnum

		client = event.client
		channel = get_config("dev.channels.logs", ignore_None=True)
		if channel:
			channel = await client.fetch_channel(channel)
		if not channel:
			print("No logging channel specified")
		ready_delta: timedelta = client.ready_at - client.started_at
		if get_config("dev.send-startup-message"):
			message = await channel.send(
			    embed=Embed(
			        description=
			        f"<t:{round(client.started_at.timestamp())}:D> <t:{round(client.started_at.timestamp())}:T>" +
			        f"(Ready: **{fnum(ready_delta.total_seconds())}**s{emojis['icons']['loading']})" + "\n" +
			        f"Git hash: {get_git_hash()}"
			    )
			)

		async def followup(timestamp: datetime):
			client.followup_at = timestamp
			loadup_delta: timedelta = client.followup_at - client.started_at
			if get_config("dev.send-startup-message"):
				embed = message.embeds[0]

				embed.description = embed.description.replace(
				    " " + emojis['icons']['loading'], f", loading took **{fnum(loadup_delta.total_seconds())}**s."
				).replace(" :i:", f", loading took **{fnum(loadup_delta.total_seconds())}**s.")

				await message.edit(embed=embed)

		if (stuff["followup_at"]):
			await followup(stuff["followup_at"])
		ReadyEvent.followup = followup
		ReadyEvent.stuff = stuff
		while True:
			await sleep(0.5)
			if len(stuff['queue']) > 0:
				for thing in stuff['queue']:
					await channel.send(embed=Embed(description=str(thing), color=Colors.BAD, title="Error"))
				stuff['queue'] = []
