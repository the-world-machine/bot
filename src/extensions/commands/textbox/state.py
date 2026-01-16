import asyncio
import re
from utilities.config import get_config
from utilities.localization import Localization
from utilities.message_decorations import Colors, fancy_message
from utilities.textbox.facepics import get_facepic
from utilities.textbox.states import State, states
from interactions import Embed, OptionType, SlashContext, slash_option

int_regex = re.compile(r"^\d+$")


@slash_option(
    name='search',
    description='sid here, special: `all` all states, `user:userid/"me"` user\'s states. at end: `!Page:Amount` (ints)',
    opt_type=OptionType.STRING,
    required=False
)
async def command_(self, ctx: SlashContext, search: str = "user:me!0:1"):
	loc = Localization(ctx)
	await fancy_message(ctx, loc.l("generic.loading.checking_developer_status"), ephemeral=True)
	if str(ctx.author.id) not in get_config('dev.whitelist', typecheck=list):
		await asyncio.sleep(3)
		return await fancy_message(
		    ctx,
		    loc.l("generic.errors.not_a_developer"),
		    facepic=await get_facepic("OneShot (fan)/Nikonlanger/Jii"),
		    edit=True
		)
	states2show: list[tuple[str, State]] = []
	options = search.split("!")
	filter = options[0]

	states2show = list(states.items())
	match filter:
		case "all":
			pass
		case _:
			if filter.startswith("user:"):
				_ = filter.split(":")
				user_id = _[1] if len(_) == 1 else "me"
				if not int_regex.match(user_id) and not user_id == "me":
					await ctx.edit(embeds=Embed(color=Colors.BAD, title="Invalid user id"))
				if user_id == "me":
					user_id = str(ctx.user.id)
				states2show = [ a for a in states2show if a[1].owner == int(user_id) ]
			elif int_regex.match(filter):
				if not filter in states:
					return await ctx.edit(embeds=Embed(color=Colors.BAD, title=f"Couldn't find sid {filter}"))
				states2show = [states[filter]]
	if len(states2show) > 0:
		paging = options[1].split(":")
		page = paging[0] if len(paging) > 0 else "0"
		items_per_page = "10"
		try:
			page = int(page)
		except:
			return await ctx.edit(embeds=Embed(color=Colors.BAD, title=f"Invalid Pages (!__{page}__:{items_per_page})"))
		items_per_page = paging[1] if len(paging) > 1 else "10"
		try:
			items_per_page = int(items_per_page)
		except:
			return await ctx.edit(
			    embeds=Embed(color=Colors.BAD, title=f"Invalid items per page (Amount) (!{page}:__{items_per_page}__)")
			)
		if page > len(states2show) * items_per_page:
			return await ctx.edit(
			    embeds=Embed(
			        color=Colors.BAD,
			        title=f"Page out of bounds, max: {len(states2show)} (!{page}:__{items_per_page}__)"
			    )
			)
		states2show = states2show[page * items_per_page:max((page * items_per_page) + items_per_page, len(states2show))]
	if len(states2show) == 0:
		return await ctx.edit(
		    embeds=Embed(
		        color=Colors.BAD,
		        title="Nothing found" +
		        (" (there are no states)" if len(states) == 0 else " (check your filter maybe?)")
		    )
		)
	print(states2show)
	return await ctx.edit(
	    embeds=Embed(
	        color=Colors.DEFAULT,
	        title=f"Found results: {len(states2show[:4000])}",
	        description='\n'.join(map(lambda a: f"-# {a[0]}:\n```{a[1]}```", states2show))
	    )
	)


exports = {command_}
