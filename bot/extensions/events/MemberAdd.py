import io
from interactions import *
from utilities.mediagen.textbox import render_frame
from interactions.api.events import MemberAdd
from utilities.database.schemas import ServerData
from utilities.localization import assign_variables
from utilities.textbox.characters import get_character


class MemberAddEvent(Extension):

	@listen(MemberAdd, delay_until_ready=True)
	async def handler(self, event: MemberAdd):
		client = event.client

		if event.member.bot:
			return
		server_data: ServerData = await ServerData(_id=event.guild_id).fetch()

		if not event.guild.system_channel or not server_data.welcome_message:
			return
		message = assign_variables(
		    server_data.welcome_message, user_name=event.member.display_name, server_name=event.guild.name
		)
		print(
		    f"Trying to send welcome message for server {event.guild.id} in channel <#{event.guild.system_channel.id}>"
		)
		buffer = io.BytesIO()
		(await render_frame(message,
		                    get_character("The World Machine").get_face("Pancakes"),
		                    False))[0].save(buffer, format="PNG")
		buffer.seek(0)
		await event.guild.system_channel.send(
		    content=event.member.mention,
		    files=File(file=buffer, file_name=f"welcome textbox.png"),
		    allowed_mentions={ 'users': []}
		)
