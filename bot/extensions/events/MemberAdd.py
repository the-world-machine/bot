from interactions import *
from utilities.media import generate_dialogue
from interactions.api.events import MemberAdd
from utilities.database.main import ServerData
from utilities.localization import assign_variables


class MemberAddEvent(Extension):

	@listen(MemberAdd, delay_until_ready=True)
	async def handler(self, event: MemberAdd):
		client = event.client

		if event.member.bot:
			return
		server_data: ServerData = await ServerData(event.guild_id).fetch()

		if not event.guild.system_channel or not server_data.welcome_message:
			return
		message = assign_variables(server_data.welcome_message, user_name=event.member.display_name, server_name=event.guild.name)
		print(f"Trying to send welcome message for server {event.guild.id} in channel <#{event.guild.system_channel.id}>")
		await event.guild.system_channel.send(
		    content=event.member.mention,
		    files=await generate_dialogue(message, 'https://cdn.discordapp.com/emojis/1023573458296246333.webp?size=128&quality=lossless'
		                                                                                                                                    # twm amazed
		                                 ),
		    allowed_mentions={ 'users': []}
		)
