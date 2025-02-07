from interactions import *
from utilities.database.main import ServerData
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message


class SettingsCommands(Extension):

	@slash_command(description="Configure the behavior of The World Machine for this server")
	async def settings(self, ctx: SlashContext):
		pass

	server = settings.group(name="server")
	transmissions = settings.group(name="transmissions")

	async def check(self, ctx: SlashContext):
		if Permissions.MANAGE_GUILD not in ctx.member.guild_permissions:
			await fancy_message(ctx, Localization(ctx.locale).l("settings.errors.missing_permissions"), color=Colors.BAD, ephemeral=True)
			return False

		return True

	@transmissions.subcommand(sub_cmd_description="The specific channel to use for calling")
	@slash_option(
	    description="default: AUTO",
	    name="channel",
	    opt_type=OptionType.CHANNEL,
	)
	async def channel(self, ctx: SlashContext, channel: GuildText = None):
		if not await self.check(ctx):
			return
		loc = Localization(ctx.locale)
		server_data = await ServerData(ctx.guild_id).fetch()
		if channel is None:
			await server_data.update(transmit_channel=None)
			return await fancy_message(ctx, loc.l("settings.transmissions.channel.auto"), ephemeral=True)
		if not isinstance(channel, MessageableMixin):
			return await fancy_message(ctx, loc.l("settings.transmissions.channel_not_messageable"), color=Colors.BAD, ephemeral=True)
		await server_data.update(transmit_channel=str(channel.id))
		return await fancy_message(
		    ctx,
		    loc.l("settings.transmissions.channel.Changed", channel=channel.mention),
		    ephemeral=True,
		)

	@transmissions.subcommand(sub_cmd_description="Disable/Enable receiving images when transmitting. All redacted images will be sent as [IMAGE]")
	@slash_option(
	    description="default: TRUE",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def images(self, ctx: SlashContext, value: bool):
		if not await self.check(ctx):
			return
		loc = Localization(ctx.locale)

		server_data = await ServerData(ctx.guild_id).fetch()

		await server_data.update(transmit_images=value)
		return await fancy_message(ctx, loc.l(f"settings.transmissions.images.{'enabled' if value else 'disabled'}"), ephemeral=True)

	@transmissions.subcommand(sub_cmd_description="Whether transmission receivers are shown Oneshot characters instead of actual people from the server")
	@slash_option(
	    description="default: TRUE",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def anonymous(self, ctx: SlashContext, value):
		if not await self.check(ctx):
			return
		loc = Localization(ctx.locale)

		server_data = await ServerData(ctx.guild_id).fetch()

		await server_data.update(transmit_anonymous=value)

		return await fancy_message(ctx, loc.l(f"settings.transmissions.anonymous.{'enabled' if value else 'disabled'}"), ephemeral=True)

	@transmissions.subcommand(sub_cmd_description="Toggle blocking a server from being able to call")
	@slash_option(
	    description="The server's ID",
	    name="server",
	    opt_type=OptionType.STRING,
	    required=True,
	    autocomplete=True,
	)
	async def block(self, ctx: SlashContext, server: str = None):
		if not await self.check(ctx):
			return
		loc = Localization(ctx.locale)
		server_data: ServerData = await ServerData(ctx.guild_id).fetch()

		block_list = server_data.blocked_servers

		try:
			server_id = int(server)
		except ValueError:
			return await ctx.reply(embed=Embed(
			    description=loc.l("settings.errors.invalid_server_id"),
			    footer=loc.l("settings.errors.get_server_id"),
			    color=Colors.BAD,
			))
		server_name = ctx.client.get_guild(server_id).name
		if server_id in block_list:
			block_list.remove(server_id)
			await server_data.update(blocked_servers=block_list)
		else:
			block_list.append(server_id)
			await server_data.update(blocked_servers=block_list)
		return await fancy_message(ctx, loc.l(f"settings.transmissions.blocked.{'yah' if server_id in block_list else 'nah'}", server_name=server_name), ephemeral=True)

	@server.autocomplete("server")
	async def block_server_autocomplete(self, ctx: AutocompleteContext):

		server_data: ServerData = await ServerData(ctx.guild_id).fetch()

		transmitted_servers = server_data.transmittable_servers

		server = ctx.input_text

		servers = []

		for server_id, server_name in transmitted_servers.items():

			if not server:
				servers.append({ "name": server_name, "value": server_id})
				continue

			if server.lower() in server_name.lower():
				servers.append({ "name": server_name, "value": server_id})

		await ctx.send(servers)

	@server.subcommand(sub_cmd_description="Edit this server's welcome message")
	async def welcome_message(self, ctx: SlashContext):
		if not await self.check(ctx):
			return
		loc = Localization(ctx.locale)
		return await ctx.send_modal(
		    Modal(
		        InputText(
		            label=loc.l("settings.server.welcome.editor.input"),
		            style=TextStyles.PARAGRAPH,
		            custom_id="message",
		            placeholder=loc.l("settings.server.welcome.editor.placeholder"),
		            max_length=200,
		            required=False,
		        ),
		        title=loc.l("settings.server.welcome.editor.title"),
		        custom_id="welcome_message_editor",
		    )
		)

	@modal_callback("welcome_message_editor")
	async def welcome_message_editor(self, ctx: ModalContext, message: str):

		server_data: ServerData = await ServerData(ctx.guild_id).fetch()
		await server_data.update(welcome_message=message)
		message = f"```\n{message.replace('```', '` ``')}```"

		await ctx.send(Localization(ctx.locale).l("settings.server.welcome.editor.done") + message, ephemeral=True)
