from interactions import *
from utilities.config import debugging, get_config
from utilities.database.schemas import ServerData
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message


class SettingsCommands(Extension):

	@slash_command(description="Configure the behavior of The World Machine for this server")
	@integration_types(guild=True, user=False)
	@contexts(bot_dm=False)
	async def settings(self, ctx: SlashContext):
		pass

	async def channel_permission_check(self, loc, ctx: SlashContext, channel: GuildText) -> bool:
		if not isinstance(channel, MessageableMixin):
			await fancy_message(
			    ctx,
			    loc.l("settings.errors.channel_not_messageable"),
			    color=Colors.BAD,
			)
			return False
		required_perms = Permissions.SEND_MESSAGES | Permissions.VIEW_CHANNEL | Permissions.ATTACH_FILES
		channel_perms = channel.permissions_for(ctx.guild.me)
		has_perms = (channel_perms & required_perms) == required_perms
		if not has_perms:
			await fancy_message(
			    ctx,
			    loc.l("settings.errors.channel_insufficient_perms"),
			    color=Colors.BAD,
			)
		return True

	async def permission_check(self, loc, ctx: SlashContext):
		member = ctx.guild.get_member(ctx.user.id)
		if not member:
			await fancy_message(ctx, loc.l("settings.errors.weird_edgecase_number_0"), color=Colors.BAD, ephemeral=True)
			return False

		if not ctx.member.has_permission(Permissions.MANAGE_GUILD):
			await fancy_message(ctx, loc.l("settings.errors.missing_permissions"), color=Colors.BAD, ephemeral=True)
			return False

		return True

	async def basic(self, ctx: SlashContext) -> tuple[Localization, ServerData]:
		loc = Localization(ctx.locale)
		if not await self.permission_check(loc, ctx):
			return
		await ctx.defer(ephemeral=True)
		server_data: ServerData = await ServerData(ctx.guild.id).fetch()
		return (loc, server_data)

	transmissions = settings.group(name="transmissions")

	@transmissions.subcommand(sub_cmd_description="Toggle this server's ability to receive calls")
	@slash_option(
	    description="default: True",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def enabled(self, ctx: SlashContext, value):
		loc, server_data = await self.basic(ctx)

		await server_data.welcome.update(disabled=not value)

		return await fancy_message(
		    ctx, loc.l(f"settings.transmissions.anonymous.{'enabled' if value else 'disabled'}"), ephemeral=True
		)

	@transmissions.subcommand(sub_cmd_description="Channel to be used by default when accepting calls")
	@slash_option(
	    description="(omit option to reset) default: Current",
	    name="channel",
	    opt_type=OptionType.CHANNEL,
	)
	async def channel(self, ctx: SlashContext, channel: GuildText = None):
		loc, server_data = await self.basic(ctx)

		if channel is None:
			await server_data.transmissions.update(channel_id=None)
			return await fancy_message(ctx, loc.l("settings.transmissions.channel.auto"), ephemeral=True)

		if not await self.channel_permission_check(loc, ctx, channel):
			return

		await server_data.transmissions.update(channel_id=str(channel.id))
		return await fancy_message(
		    ctx, loc.l("settings.transmissions.channel.Changed", channel=channel.mention), ephemeral=True
		)

	@transmissions.subcommand(sub_cmd_description="Toggle embedding images when transmitting")
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
		    ) + (("\n-# " + loc.l("settings.errors.uncached_server")) if not guild else ""),
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
		  guild.id if isinstance(guild, Guild) else guild: guild.name if isinstance(guild, Guild) else (loc.l("transmit.autocomplete.unknown_server", server_id=guild), True)
		  for guild in guilds
		}
		# yapf: enable

		server = ctx.input_text

		filtered_servers = []

		for server_id, server_name in servers.items():
			if isinstance(server_name, tuple):
				filtered_servers.append({ "name": server_name[0], "value": server_id})
				continue

			if server.lower() in server_name.lower():
				filtered_servers.append({ "name": server_name, "value": server_id})

		await ctx.send(filtered_servers)

	welcome = settings.group(name="welcome")

	@welcome.subcommand(sub_cmd_description="Whether to send the welcome textbox when someone joins")
	@slash_option(
	    description="default: False",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def enabled(self, ctx: SlashContext, value):
		loc, server_data = await self.basic(ctx)

		await server_data.welcome.update(disabled=not value)

		return await fancy_message(ctx, loc.l(f"settings.welcome.enabled.{'yah' if value else 'nah'}"), ephemeral=True)

	@welcome.subcommand(sub_cmd_description="Whether to ping the newcomers (shows the @mention regardless)")
	@slash_option(
	    description="default: False",
	    name="value",
	    opt_type=OptionType.BOOLEAN,
	    required=True,
	)
	async def ping(self, ctx: SlashContext, value):
		loc, server_data = await self.basic(ctx)

		await server_data.welcome.update(ping=not value)

		return await fancy_message(ctx, loc.l(f"settings.welcome.ping.{'yah' if value else 'nah'}"), ephemeral=True)

	@welcome.subcommand(sub_cmd_description="Edit this server's welcome message")
	async def edit(self, ctx: SlashContext):
		loc = Localization(ctx.locale)
		if not await self.permission_check(loc, ctx):
			return
		server_data = await ServerData(ctx.guild_id).fetch()

		return await ctx.send_modal(
		    Modal(
		        InputText(
		            label=loc.l("settings.server.welcome.editor.input"),
		            style=TextStyles.PARAGRAPH,
		            custom_id="text",
		            placeholder=loc.l("settings.server.welcome.editor.placeholder"),
		            max_length=get_config("textbox.max-text-length-per-frame", ignore_None=True) or 1423,
		            required=False,
		            value=server_data.welcome.message or loc.l("misc.welcome.placeholder_text")
		        ),
		        title=loc.l("settings.server.welcome.editor.title"),
		        custom_id="welcome_message_editor",
		    )
		)

	@modal_callback("welcome_message_editor")
	async def welcome_message_editor(self, ctx: ModalContext, text: str):
		warn = ""
		loc = Localization(ctx.locale)
		server_data: ServerData = await ServerData(ctx.guild_id).fetch()
		config = server_data.welcome
		old_text = config.message
		new_text = text
		if text == loc.l("misc.welcome.placeholder_text"):
			new_text = None

		await config.update(message=new_text)

		old_text = f"```\n{old_text.replace('```', '` ``')}```"
		new_text = f"```\n{text.replace('```', '` ``')}```"

		if config.disabled:
			warn = "\n-# " + loc.l("settings.server.welcome.editor.disabled_warning")
		debug = ""
		if debugging():
			debug = loc.l("settings.server.welcome.editor.debug", old_text=old_text, new_text=new_text)
		await fancy_message(ctx, loc.l("settings.server.welcome.editor.done") + debug + warn, ephemeral=True)

	@welcome.subcommand(sub_cmd_description="Where to send the welcome textboxes to")
	@slash_option(
	    description="(omit option to reset) default: Server Settings -> System Messages channel",
	    name="channel",
	    opt_type=OptionType.CHANNEL,
	)
	async def channel(self, ctx: SlashContext, channel: GuildText = None):
		loc, server_data = await self.basic(ctx)
		config = server_data.welcome
		if channel is None:
			await config.update(channel_id=None)
			return await fancy_message(ctx, loc.l("settings.server.welcome.channel.auto"), ephemeral=True)
		if not await self.channel_permission_check(loc, ctx, channel):
			return
		await config.update(channel_id=str(channel.id))

		warn = ""
		if config.disabled:
			warn += "\n-# " + loc.l("settings.server.welcome.editor.disabled_warning")
		if not config.message:
			warn += "\n-# " + loc.l("settings.server.welcome.enabled.edit_warning")
		return await fancy_message(
		    ctx,
		    loc.l("settings.server.welcome.channel.Changed", channel=channel.mention) + warn,
		)
