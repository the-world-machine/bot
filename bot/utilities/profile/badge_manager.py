import utilities.database.main as db
from interactions import *
from utilities.message_decorations import Colors
from utilities.shop.fetch_items import fetch_badge

import aiofiles
import json


async def earn_badge(ctx: GuildChannel,
                     badge_name: str,
                     badge_data: dict,
                     target: User,
                     send_message: bool = True):
	channel = ctx

	user_data = await db.UserData(target.id).fetch()

	emoji = PartialEmoji(id=badge_data['emoji'])

	type_descrim = {
	    'times_shattered':
	        f' earned the <:{emoji.name}:{emoji.id}> **{badge_name}** by shattering a lightbulb **{badge_data["requirement"]}** times!',
	    'times_asked':
	        f' earned the <:{emoji.name}:{emoji.id}> **{badge_name}** by bothering The World Machine **{badge_data["requirement"]}** times!',
	    'wool':
	        f' earned the <:{emoji.name}:{emoji.id}> **{badge_name}** by earning over **{badge_data["requirement"]}** wool!',
	    'times_transmitted':
	        f' earned the <:{emoji.name}:{emoji.id}> **{badge_name}** by transmitting **{badge_data["requirement"]}** times!',
	    'suns':
	        f' earned the <:{emoji.name}:{emoji.id}> **{badge_name}** by giving/earning **{badge_data["requirement"]}** suns!'
	}

	embed = Embed(
	    title='You got a badge!',
	    description=f'<@{int(target.id)}>{type_descrim[badge_data["type"]]}',
	    color=Colors.YELLOW)

	embed.set_footer(
	    'You can change this notification using "/settings badge_notifications"'
	)

	owned_badges = user_data.owned_badges
	owned_badges.append(badge_name)

	await user_data.update(owned_badges=owned_badges)

	if user_data.badge_notifications and send_message:
		return await channel.send(embeds=embed)


async def increment_value(ctx: SlashContext,
                          value_to_increment: str,
                          amount: int = 1,
                          target: User = None):
	badges = await fetch_badge()

	guild = ctx.channel

	if guild.type == ChannelType.DM:
		return

	if target:
		user = target
	else:
		user = ctx.author

	user_data = await db.UserData(user.id).fetch()
	json_data = user_data.__dict__

	await user_data.increment_value(value_to_increment, amount)

	get_value = json_data[value_to_increment] + amount

	for badge, data in badges.items():
		if data['type'] == value_to_increment:
			if badge in user_data.owned_badges:
				continue

			if get_value < data['requirement']:
				continue

			send_message = True

			if get_value > data['requirement']:
				send_message = False

			return await earn_badge(guild, badge, data, user, send_message)
