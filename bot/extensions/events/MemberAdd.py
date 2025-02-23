import traceback as tb
from interactions import *
from utilities.media import generate_dialogue
from interactions.api.events import MemberAdd
from utilities.database.schemas import ServerData
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
		if config.channel_id and config.channel_id in list(map(lambda c: c.id, guild.channels)):
			target_channel = guild.get_channel(config.channel_id)

		if not target_channel:
			return

		message = config.message if config.message else loc.l("misc.welcome.placeholder_message")

		message = assign_variables(message, user_name=event.member.display_name, server_name=guild.name)
		try:
			await guild.system_channel.send(
			    content=f"-# {event.member.mention}",
			    files=await generate_dialogue(
			        message, 'https://cdn.discordapp.com/emojis/1023573458296246333.webp?size=128&quality=lossless'
			    ),
			    allowed_mentions=AllowedMentions.all() if server_data.welcome.ping else AllowedMentions.none()
			)
		except Exception as e:
			print("Failed to send welcome message. {guild.id}/{target_channel.id}")
			print(tb.format_exc(chain=True))
			config.update(enabled=False)
