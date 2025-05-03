import io
import traceback as tb
from interactions import *
from utilities.mediagen.textboxes import render_textbox
from interactions.api.events import MemberAdd
from utilities.database.schemas import ServerData
from utilities.textbox.characters import get_character
from utilities.localization import Localization, assign_variables


class MemberAddEvent(Extension):

	@listen(MemberAdd, delay_until_ready=True)
	async def handler(self, event: MemberAdd):
		if event.member.bot:
			return
		guild = event.guild
		loc = Localization(guild.preferred_locale)
		server_data: ServerData = await ServerData(_id=guild.id).fetch()
		config = server_data.welcome

		if config.disabled:
			return

		target_channel = guild.system_channel
		channels = list(map(lambda c: str(c.id), guild.channels))
		if config.channel_id and config.channel_id in channels:
			target_channel = guild.get_channel(config.channel_id)

		if not target_channel:
			return

		message = config.message or loc.l("misc.welcome.placeholder_text")

		message = assign_variables(
		    message, user_name=event.member.display_name, server_name=guild.name, member_count=guild.member_count
		)
		buffer = io.BytesIO()
		(await render_textbox(message,
		                      get_character("The World Machine").get_face("Pancakes"),
		                      False))[0].save(buffer, format="PNG")
		buffer.seek(0)
		try:
			print(
			    f"Trying to send welcome message for server {event.guild.id} in channel <#{event.guild.system_channel.id}>"
			)
			await target_channel.send(
			    content=f"-# {event.member.mention}",
			    files=File(file=buffer, file_name=f"welcome textbox.png"),
			    allowed_mentions=AllowedMentions.all() if server_data.welcome.ping else AllowedMentions.none()
			)
		except Exception as e:
			print("Failed to send welcome message. {guild.id}/{target_channel.id}")
			print(tb.format_exc(chain=True))
			await config.update(enabled=False, errored=True)
