from interactions import Extension, listen
from interactions.api.events import Ready

class Logs(Extension):

	@listen(Ready, delay_until_ready=True)
	async def send_logs(self, event: Ready):
		if hasattr(event.client, "followup_message_edited_at"):  # type:ignore
			from extensions.events.Ready import ReadyEvent
			await ReadyEvent.log(lambda channel: channel.send(content="Ready event triggered!"))
