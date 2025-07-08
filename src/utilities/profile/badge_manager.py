from utilities.database.main import to_dict
from utilities.database.schemas import UserData
from interactions import *
from utilities.message_decorations import Colors
from utilities.shop.fetch_items import fetch_badge


async def earn_badge(ctx: SlashContext, badge_name: str, badge_data: dict, target: User, send_message: bool = True):
	user_data = await UserData(_id=target.id).fetch()

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
	    color=Colors.YELLOW
	)

	embed.set_footer('You can change this notification using "/settings badge_notifications"')

	owned_badges = user_data.owned_badges
	await owned_badges.append(badge_name)

	await user_data.update(owned_badges=owned_badges)

	if user_data.badge_notifications and send_message:
		return await ctx.send(embeds=embed)


async def increment_value(ctx: SlashContext, value_to_increment: str, amount: int = 1, target: User = None):
	badges = await fetch_badge()

	if target:
		user = target
	else:
		user = ctx.author

	user_data = await UserData(_id=user.id).fetch()
	user_dict = to_dict(user_data)

	await user_data.increment_key(value_to_increment, amount)

	get_value = user_dict[value_to_increment] + amount

	for badge, data in badges.items():
		if data['type'] == value_to_increment:
			if badge in user_data.owned_badges:
				continue

			if get_value < data['requirement']:
				continue

			send_message = True

			if get_value > data['requirement']:
				send_message = False

			return await earn_badge(ctx, badge, data, user, send_message)
