from interactions import *
from interactions.api.events import Ready
# Should serve as an example event file, otherwise should've remained in main.py


class ReadyEvent(Extension):

	@listen(Ready)
	async def handler(self, event: Ready):
		client = event.client    # <- this is always defined on `event`
		print(f"─ Started Discord as {client.user.tag} ({client.user.id})")
