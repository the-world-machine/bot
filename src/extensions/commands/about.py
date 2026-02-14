import psutil
import platform
from datetime import datetime, timezone
from utilities.misc import get_git_hash
from utilities.localization import Localization, amperjoin, fnum, ftime
from utilities.message_decorations import Colors, fancy_message
from interactions import ActionRow, Button, ButtonStyle, Embed, EmbedField, Extension, Message, OptionType, SlashContext, User, contexts, integration_types, slash_command, slash_option

try:
	commit_hash = get_git_hash()
	print(f"Found git hash: {commit_hash}")
except Exception as e:
	print(f"Error retrieving git hash: {e}")


class AboutCommand(Extension):

	@slash_command(description='About the bot (ping, stats)')
	@slash_option(
	    description="Whether you want the response to be visible for others in the channel",
	    name="public",
	    opt_type=OptionType.BOOLEAN
	)
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def about(self, ctx: SlashContext, public: bool = False):
		loc = Localization(ctx)
		start_time = datetime.now(timezone.utc)
		_ = await fancy_message(ctx, loc.l("generic.loading.hint"), ephemeral=not public)
		if not isinstance(_, Message):
			return

		reception_latency = start_time - datetime.fromtimestamp(ctx.id.created_at.timestamp(), tz=timezone.utc)

		reply_latency = datetime.fromtimestamp(_.created_at.timestamp(), tz=timezone.utc) - start_time

		host = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"

		def users_to_mentions(users: list[User], detail: bool = False) -> list[str]:
			return list(map(lambda user: f"<@{user.id}>" + (f" (@{user.username})" if detail else ""), users))

		buttons: list[Button] = []
		strbuttons: list[str] = []
		processed_lines: list[str] = []
		_first_processed: bool = False
		if ctx.client.app.description:
			for line in ctx.client.app.description.splitlines():
				try:
					if ': http' in line:
						name, url = line.split(':', 1)
						name = name.strip()

						loc_name = loc.l(f"about.buttons['{name.lower()}']")
						if not loc_name.startswith("`"):
							name = loc_name

						if len(buttons) < 25:
							buttons.append(Button(style=ButtonStyle.LINK, label=name, url=url.strip()))
						else:
							strbuttons.append(f"[{name}]({url})")
					else:
						if not _first_processed:
							_first_processed = True
							original_lines = loc.l(
							    "about.me's",
							)
							translated_lines = Localization().l("about.mes")

							for i in range(0, len(original_lines)):
								if not (len(translated_lines) > i) and original_lines[i] == line:
									line = translated_lines[i]
						processed_lines.append(line)
				except ValueError:
					processed_lines.append(line)

		team = ctx.client.app.team
		developers: list[User] = [ctx.client.app.owner]
		if team:
			developers = [member.user for member in team.members]
		contributors: list[User] = []
		translators: list[User] = []
		donators: list[User] = []
		# TODO: fetch those from config.yml role ids
		description = '\n'.join(
		    [
		        s for s in (
		            f"👑 {amperjoin(users_to_mentions(developers, detail=True))}",
		            f"🧑‍💻 {amperjoin(users_to_mentions(contributors))}" if len(contributors) > 0 else None,
		            f"✍️ {amperjoin(users_to_mentions(translators))}" if len(translators) > 0 else None,
		            f"💸 {amperjoin(users_to_mentions(donators))}" if len(donators) > 0 else None, "",
		            "\n".join(processed_lines)
		        ) if s is not None
		    ]
		)
		embed = Embed(description=description, color=Colors.DEFAULT)
		embed.add_fields(
		    EmbedField(
		        name=loc.l("about.names.avg_ping"),
		        value=loc.l("about.values.time", sec=fnum(ctx.client.latency, ctx.locale)),
		        inline=True
		    ),
		    EmbedField(
		        name=loc.l("about.names.latency"),
		        value=
		        f'{loc.l("about.values.time", sec=fnum(reception_latency.microseconds / 1e6, ctx.locale))} / {loc.l("about.values.time", sec=fnum(reply_latency.microseconds / 1e6, ctx.locale))}',
		        inline=True
		    ),
		    EmbedField(
		        name=loc.l("about.names.cpu_usg"),
		        value=loc.l("about.values.percent", num=round(psutil.cpu_percent())),
		        inline=True
		    ),
		    EmbedField(
		        name=loc.l("about.names.mem_usg"),
		        value=loc.l("about.values.percent", num=round(psutil.virtual_memory().percent)),
		        inline=True
		    ), EmbedField(name=loc.l("about.names.server_count"), value=str(ctx.client.guild_count), inline=True),
		    EmbedField(
		        name=loc.l("about.names.commit_hash"),
		        value=commit_hash if commit_hash else loc.l("misc.status.values.failed_commit_hash"),
		        inline=True
		    ),
		    EmbedField(
		        loc.l("about.names.uptime"), ftime(datetime.now() - ctx.client.start_time, ctx.locale), inline=True
		    )
		)
		# embed.add_field(loc.l("about.names.user_installs"),
		#                 len(ctx.client.app.users)) # NONEXISTENT
		embed.add_field(loc.l("about.names.host"), host, inline=True)
		rows = []
		for i in range(0, len(buttons), 5):
			rows.append(ActionRow(*buttons[i:i + 5]))
		return await ctx.edit(embeds=[embed], components=rows)
