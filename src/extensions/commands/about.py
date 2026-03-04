import platform
from datetime import datetime, timezone

from interactions import (
	ActionRow,
	Button,
	ButtonStyle,
	Embed,
	EmbedField,
	Extension,
	OptionType,
	SlashContext,
	contexts,
	integration_types,
	slash_command,
	slash_option,
)

from utilities.emojis import emojis
from utilities.localization.formatting import fnum, ftime
from utilities.localization.localization import Localization, source_loc
from utilities.message_decorations import Colors, fancy_message
from utilities.stats import get_stats, get_version


class AboutCommand(Extension):
	@slash_command(description="About the bot (ping, stats)")
	@slash_option(
		description="Whether you want the response to be visible for others in the channel",
		name="public",
		opt_type=OptionType.BOOLEAN,
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def about(self, ctx: SlashContext, public: bool = False):
		start_time = datetime.now(timezone.utc)

		loading_message = await fancy_message(ctx, f"-# {emojis['icons']['loading']}", ephemeral=not public)

		reception_latency = start_time - datetime.fromtimestamp(ctx.id.created_at.timestamp(), tz=timezone.utc)

		reply_latency = datetime.fromtimestamp(loading_message.created_at.timestamp(), tz=timezone.utc) - start_time

		loc = Localization(ctx)
		stats_loc = Localization(ctx, prefix="commands.stats.commands.about")
		buttons: list[Button] = []
		strbuttons: list[str] = []
		processed_lines: list[str] = []
		_first_processed: bool = False
		if ctx.client.app.description:
			for line in ctx.client.app.description.splitlines():
				try:
					if ": http" in line or ":http" in line:
						name, url = line.split(":", 1)
						name = name.strip()

						loc_name = await loc.format(stats_loc.l(f"buttons['{name.lower()}']"))
						if not loc_name.startswith("`"):
							name = loc_name

						if len(buttons) < 25:
							buttons.append(Button(style=ButtonStyle.LINK, label=name, url=url.strip()))
						else:
							strbuttons.append(f"[{name}]({url})")
					else:
						if not _first_processed:
							_first_processed = True
							original_lines = list(await source_loc.format(source_loc.l("mes", typecheck=tuple)))
							translated_lines = list(await loc.format(stats_loc.l("mes", typecheck=tuple)))
							index = original_lines.index(line)
							line = translated_lines[index]
						processed_lines.append(line)
				except ValueError:
					processed_lines.append(line)

		team = ctx.client.app.team
		processed_description = "\n".join(processed_lines)

		if len(strbuttons) != 0:
			processed_description += "\n" + (" · ".join(strbuttons))
		sys_stats = get_stats()
		version = get_version()
		embed = Embed(description=processed_description, color=Colors.DEFAULT)  # fixme: no way to see owners now
		embed.add_fields(
			EmbedField(
				name=await loc.format(stats_loc.l("fields.avg_ping.name")),
				value=await loc.format(stats_loc.l("generic_values.time"), sec=fnum(ctx.client.latency, ctx.locale)),
				inline=True,
			),
			EmbedField(
				name=await loc.format(stats_loc.l("fields.latency.name")),
				value=f"{await loc.format(stats_loc.l('generic_values.time'), sec=fnum(reception_latency.microseconds / 1e6, ctx.locale))} / {await loc.format(stats_loc.l('generic_values.time'), sec=fnum(reply_latency.microseconds / 1e6, ctx.locale))}",
				inline=True,
			),
			EmbedField(
				await loc.format(stats_loc.l("fields.uptime.name")),
				ftime(datetime.now() - ctx.client.start_time, ctx.locale),
				inline=True,
			),
			EmbedField(
				name=await loc.format(stats_loc.l("fields.server_count.name")),
				value=str(ctx.client.guild_count),
				inline=True,
			),
			EmbedField(
				name=await loc.format(stats_loc.l("fields.load.name")),
				value=await loc.format(
					stats_loc.l("fields.load.value"),
					cpu_load=sys_stats.cpu / 100,
					mem_load=sys_stats.ram / 100,
				),
				inline=True,
			),
			EmbedField(
				name=await loc.format(stats_loc.l("fields.version.name")),
				value=await loc.format(
					stats_loc.l("fields.version.value"),
					version_type="tag" if version.tag is None else "commit",
					tag=version.tag,
					commit_hash=version.commit,
					last_updated_at=version.last_updated_at,
				),
				inline=True,
			),
			EmbedField(
				await loc.format(stats_loc.l("fields.host.name")),
				f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
				inline=True,
			),
		)
		# embed.add_field(await loc.format(stats_loc.l("fields.user_installs.name")), len(ctx.client.app.users))  # NONEXISTENT  # noqa: ERA001
		rows = []
		for i in range(0, len(buttons), 5):
			rows.append(ActionRow(*buttons[i : i + 5]))
		return await ctx.edit(embeds=[embed], components=rows)
