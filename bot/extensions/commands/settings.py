from interactions import *
from utilities.database.schemas import ServerData
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message


class SettingsCommands(Extension):

	@slash_command(description="Configure the behavior of The World Machine for this server")
	@integration_types(guild=True, user=False)
	@contexts(bot_dm=False)
	async def settings(self, ctx: SlashContext):
		pass

	server = settings.group(name="server")
	welcome = server.group(name="welcome")
	transmissions = settings.group(name="transmissions")

	async def permission_check(self, ctx: SlashContext, loc):
		member = ctx.guild.get_member(ctx.user.id)
		if not member:
			await fancy_message(ctx, loc.l("settings.errors.weird_edgecase_number_0"), color=Colors.BAD, ephemeral=True)
			return False

		if not ctx.member.has_permission(Permissions.MANAGE_GUILD):
			await fancy_message(ctx, loc.l("settings.errors.missing_permissions"), color=Colors.BAD, ephemeral=True)
			return False

		return True

	async def basic(self, ctx) -> tuple[Localization, ServerData]:
		loc = Localization(ctx.locale)
		if not await self.permission_check(ctx, loc):
			return
		await ctx.defer(ephemeral=True)

		return (loc, await ServerData(ctx.guild.id).fetch())

	@transmissions.subcommand(sub_cmd_description="The specific channel to use for calling")
	@slash_option(
	    description="(omit option to reset) default: Current",
	    name="channel",
	    opt_type=OptionType.CHANNEL,
	)
	async def channel(self, ctx: SlashContext, channel: GuildText = None):
		loc, server_data = self.basic(ctx)

		if channel is None:
			await server_data.transmissions.update(channel_id=None)
			return await fancy_message(ctx, loc.l("settings.transmissions.channel.auto"), ephemeral=True)

		if not isinstance(channel, MessageableMixin):
			return await fancy_message(
			    ctx,
			    loc.l("settings.errors.channel_not_messageable"),
			    color=Colors.BAD,
			)
		await server_data.transmissions.update(channel_id=str(channel.id))
		return await fancy_message(
		    ctx,
		    loc.l("settings.transmissions.channel.Changed", channel=channel.mention),
		)

	@transmissions.subcommand(
	    sub_cmd_description=
	    "Disable/Enable receiving images when transmitting. All redacted images will be sent as [IMAGE]"
	)
	@slash_option(
	    description="default: True",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def images(self, ctx: SlashContext, value: bool):
		loc, server_data = await self.basic(ctx)

		await server_data.transmissions.update(allow_images=value)
		return await fancy_message(
		    ctx, loc.l(f"settings.transmissions.images.{'enabled' if value else 'disabled'}"), ephemeral=True
		)

	@transmissions.subcommand(
	    sub_cmd_description=
	    "Whether transmission receivers are shown Oneshot characters instead of actual people from the server"
	)
	@slash_option(
	    description="default: False",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def anonymous(self, ctx: SlashContext, value):
		loc, server_data = await self.basic(ctx)

		await server_data.transmissions.update(anonymous=value)

		return await fancy_message(
		    ctx, loc.l(f"settings.transmissions.anonymous.{'enabled' if value else 'disabled'}"), ephemeral=True
		)

	@transmissions.subcommand(sub_cmd_description="Toggle blocking a server from being able to call")
	@slash_option(
	    description="The server's ID",
	    name="server",
	    opt_type=OptionType.STRING,
	    required=True,
	    autocomplete=True,
	)
	async def block(self, ctx: SlashContext, server: str = None):
		loc, server_data = await self.basic(ctx)

		blocklist = server_data.transmissions.blocked_servers

		try:
			server_id = int(server)
			guild = ctx.client.get_guild(server_id)
		except ValueError:
			return await ctx.reply(
			    embed=Embed(
			        description=loc.l("settings.errors.invalid_server_id") + "\n-# " +
			        loc.l("settings.errors.get_server_id"),
			        color=Colors.BAD,
			    )
			)
		if server_id in blocklist:
			blocklist.remove(server_id)
		else:
			blocklist.append(server_id)

		return await fancy_message(
		    ctx,
		    loc.l(
		        f"settings.transmissions.blocked.{'yah' if server_id in blocklist else 'nah'}",
		        server_name=guild.name if guild else server_id
		    ) + ("\n-# " + loc.l("settings.errors.uncached_server" if not guild else "")),
		    ephemeral=True
		)

	@block.autocomplete("server")
	async def block_server_autocomplete(self, ctx: AutocompleteContext):
		server_data: ServerData = await ServerData(_id=ctx.guild_id).fetch()
		loc = Localization(ctx.locale)
		guilds = [
		    await ctx.client.fetch_guild(id) or id
		    for id in list(set(server_data.transmissions.known_servers + server_data.transmissions.blocked_servers))
		]
		# yapf: disable
		servers = {
		 guild.id if isinstance(guild, Guild) else guild
		 :
                     guild.name if isinstance(guild, Guild) else (loc.l("transmit.autocomplete.unknown_server", server_id=guild), True)
		 for guild in guilds
		}
		# yapf: enable

		server = ctx.input_text

		filtered_servers = []

		for server_id, server_name in servers.items():
			if isinstance(server_name, tuple):
				servers.append({ "name": server_name[0], "value": server_id})
				continue

			if server.lower() in server_name.lower():
				servers.append({ "name": server_name, "value": server_id})

		await ctx.send(filtered_servers)

	@welcome.subcommand(sub_cmd_description="Edit this server's welcome message")
	async def edit(self, ctx: SlashContext):
		loc = Localization(ctx.locale)
		if not await self.permission_check(ctx, loc):
			return

		await ServerData(ctx.guild_id).fetch()
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

	@transmissions.subcommand(sub_cmd_description="Whether to send the welcome textbox when someone joins")
	@slash_option(
	    description="default: False",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def enabled(self, ctx: SlashContext, value):
		loc, server_data = self.basic(ctx)

		await server_data.welcome.update(disabled=not value)

		return await fancy_message(
		    ctx, loc.l(f"settings.transmissions.anonymous.{'enabled' if value else 'disabled'}"), ephemeral=True
		)

	@modal_callback("welcome_message_editor")
	async def welcome_message_editor(self, ctx: ModalContext, message: str):

		server_data: ServerData = await ServerData(ctx.guild_id).fetch()
		await server_data.welcome.update(message=message)
		message = f"```\n{message.replace('```', '` ``')}```"

		await ctx.send(Localization(ctx.locale).l("settings.server.welcome.editor.done") + message, ephemeral=True)

	@welcome.subcommand(sub_cmd_description="The specific channel to send the welcome textboxes to")
	@slash_option(
	    description="(omit option to reset) default: Server Settings -> System Messages channel",
	    name="channel",
	    opt_type=OptionType.CHANNEL,
	)
	async def channel(self, ctx: SlashContext, channel: GuildText = None):
		loc, server_data = self.basic(ctx)

		if channel is None:
			await server_data.welcome.update(channel_id=None)
			return await fancy_message(ctx, loc.l("settings.welcome.channel.auto"), ephemeral=True)

		if not isinstance(channel, MessageableMixin):
			return await fancy_message(
			    ctx,
			    loc.l("settings.errors.channel_not_messageable"),
			    color=Colors.BAD,
			)
		await server_data.transmissions.update(channel_id=str(channel.id))
		return await fancy_message(
		    ctx,
		    loc.l("settings.transmissions.channel.Changed", channel=channel.mention),
		)
