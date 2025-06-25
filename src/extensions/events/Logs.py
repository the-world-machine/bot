from interactions import Extension, listen
from interactions.api.events import Ready

class Logs(Extension):

	@listen(Ready, delay_until_ready=True)
	async def send_logs(self, event: Ready):
		from extensions.events.Ready import ReadyEvent
		ReadyEvent.log(lambda channel: channel.send(
			content="5"
		), error=False)