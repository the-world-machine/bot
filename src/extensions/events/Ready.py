from asyncio import sleep
from datetime import datetime, timedelta
from typing import Any, Callable
from interactions import Embed, Extension, Message, TYPE_MESSAGEABLE_CHANNEL, listen
from interactions.api.events import Ready
from utilities.config import get_config
from utilities.message_decorations import Colors
from utilities.misc import get_git_hash
from utilities.emojis import emojis

stuff = {
    "started": False,
    "queue": [],
    "followup_at":
        None  # datetime | bool,,,,,,,,,, this becomes Boolean after the first follow up, you can access the datetime version this in clilent.followup_at
}


class ReadyEvent(Extension):
	# WHY DID I MAKE THIS
	@staticmethod
	def log(thing: Callable[[TYPE_MESSAGEABLE_CHANNEL], Any] | Any, error: bool = True):
		print(
		    f"Queueing some{'thing' if not error else ' error'} into the log: {thing}, queue size will be: {len(stuff['queue'])+1}"
		)
		stuff['queue'].append({ "thing": thing, "error": error})

	@staticmethod
	async def followup(timestamp: datetime):
		stuff["followup_at"] = timestamp

	@listen(Ready)
	async def ready(self, event: Ready):
		client = event.client  # <- client is always defined on `event`
		print(f"─ Logged into Discord as {client.user.tag} ({client.user.id})")

	@listen(Ready)
	async def send_logs(self, event: Ready):
		if stuff['started']:
			return
		stuff['started'] = True  # yapf: ignore
		# this exists to prevent sending more "ready" messages whenever discord disconnects (ready event may fire again)

		client = event.client

		client.ready_at = datetime.now()  # type: ignore
		self.ready_at = client.ready_at  # type: ignore
		from utilities.localization import fnum

		client = event.client
		channel = get_config("dev.channels.logs", ignore_None=True, typecheck=str)
		if channel:
			channel = await client.fetch_channel(channel)

		extended = get_config("dev.channels.logs", ignore_None=True, typecheck=str)
		if extended:
			extended = await client.fetch_channel(extended)
		if not isinstance(channel, TYPE_MESSAGEABLE_CHANNEL):
			return print("erorrrrrrr: logs channel id is not of messageable type")
		if not isinstance(extended, TYPE_MESSAGEABLE_CHANNEL):
			return print("erorrrrrrr: extended logs channel id is not of messageable type")
		ready_delta: timedelta = client.ready_at - client.started_at  # type: ignore
		message: Message | None  # type:ignore
		if get_config("dev.send-startup-message", typecheck=bool):
			message = await channel.send(
			    embed=Embed(
			        description=
			        f"<t:{round(client.started_at.timestamp())}:D> <t:{round(client.started_at.timestamp())}:T>"  # type: ignore
			        +  # type: ignore
			        f"(Ready: **{fnum(ready_delta.total_seconds())}**s {emojis['icons']['loading']})" + "\n" +
			        f"Git hash: {get_git_hash()}"
			    )
			)

		async def followup(timestamp: datetime):  #
			nonlocal message
			assert message is not None
			client.followup_at = timestamp  # type: ignore
			loadup_delta: timedelta = client.followup_at - client.started_at  # type: ignore
			if get_config("dev.send-startup-message", typecheck=bool):
				embed = message.embeds[0]
				assert embed.description is not None
				embed.description = embed.description.replace(
				    " " + emojis['icons']['loading'], f", loading took **{fnum(loadup_delta.total_seconds())}**s."
				).replace(" :i:", f", loading took **{fnum(loadup_delta.total_seconds())}**s.")

				message = await message.edit(embed=embed)
				client.followup_message_edited_at = message.edited_timestamp  # type: ignore

		if (isinstance(stuff["followup_at"], datetime)):
			await followup(stuff["followup_at"])
		ReadyEvent.followup = followup
		ReadyEvent.stuff = stuff
		while True:
			await sleep(0.5)
			if len(stuff['queue']) > 0:
				for log in stuff['queue']:
					if log["error"]:
						await channel.send(
						    embed=Embed(description=str(log["thing"]), color=Colors.BAD, title="Error"),
						    allowed_mentions={ "parse": []}
						)
					else:
						await log["thing"](channel)
					stuff['queue'].remove(log)
