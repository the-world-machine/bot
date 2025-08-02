import re
import random
from typing import get_args
from dataclasses import asdict
from collections import Counter
from utilities.emojis import emojis
from datetime import datetime, timedelta
from interactions.api.events import Ready
from utilities.message_decorations import *
from utilities.localization import Localization, fnum
from utilities.database.schemas import Nikogotchi, UserData
from utilities.shop.fetch_items import fetch_background, fetch_item, fetch_treasure
from utilities.shop.fetch_shop_data import Item, ShopData, StockData, TreasureTypes, fetch_shop_data, reset_shop_data
from interactions import ActionRow, Button, ButtonStyle, ComponentContext, Embed, EmbedAttachment, Extension, PartialEmoji, SlashContext, StringSelectMenu, StringSelectOption, component_callback, contexts, integration_types, listen, slash_command


def pancake_id_to_emoji_index_please_rename_them_in_db(
    pancake_id: Literal['pancakes', 'golden_pancakes', 'glitched_pancakes']
):
	if pancake_id == 'pancakes':
		return 'normal'
	elif pancake_id == 'golden_pancakes':
		return 'golden'
	elif pancake_id == 'glitched_pancakes':
		return 'glitched'


daily_shop: ShopData = ShopData(
    last_updated=datetime(2000, 1, 1), background_stock=[], treasure_stock=[], stock=StockData(0, 0), motd=0
)


class ShopCommands(Extension):
	global daily_shop
	max_buy_sell_limit = 1000000000000000000000000

	@listen(Ready)
	async def loadde_shoppe(self, event: Ready):
		await self.load_shop()

	async def load_shop(self):
		global daily_shop
		data = await fetch_shop_data()
		if daily_shop.last_updated.year == 2000:
			daily_shop = data
		elif datetime.now() > data.last_updated + timedelta(days=1):
			print("Resetting daily shop")
			daily_shop = await reset_shop_data()
		print("Got daily_shop")

	@component_callback('select_treasure_sell')
	async def select_treasure_sell_callback(self, ctx: ComponentContext):

		await ctx.defer(edit_origin=True)

		await self.load_shop()

		treasure = ctx.values[0]

		embeds, components = await self.embed_manager(ctx, 'Sell_Treasures', selected_treasure=treasure)

		await ctx.edit(embeds=embeds, components=components)

	@component_callback('select_treasure')
	async def select_treasure_callback(self, ctx: ComponentContext):

		await ctx.defer(edit_origin=True)

		await self.load_shop()

		treasure = ctx.values[0]

		embeds, components = await self.embed_manager(ctx, 'Treasures', selected_treasure=treasure)

		await ctx.edit(embeds=embeds, components=components)

	@component_callback('sell_treasure_menu')
	async def sell_treasure_callback(self, ctx: ComponentContext):

		await ctx.defer(edit_origin=True)

		await self.load_shop()

		embeds, components = await self.embed_manager(ctx, 'Sell_Treasures', selected_treasure=None)

		await ctx.edit(embeds=embeds, components=components)

	r_treasure_sell = re.compile(r'treasure_sell_(.*)_(.*)')

	@component_callback(r_treasure_sell)
	async def treasure_sell_action_callback(self, ctx: ComponentContext):
		global daily_shop

		await ctx.defer(edit_origin=True)

		loc = Localization(ctx.locale)

		await self.load_shop()

		match = self.r_treasure_sell.search(ctx.custom_id)

		if not match:
			return
		raw_tid: str = match.group(1)
		if raw_tid not in get_args(TreasureTypes):
			raise ValueError(f"Unknown treasure type: {raw_tid}")
		treasure_id: TreasureTypes = raw_tid  # type:ignore
		amount_to_sell = match.group(2)

		stock_price = daily_shop.stock.price

		user_data: UserData = await UserData(_id=ctx.author.id).fetch()

		all_treasures = await fetch_treasure()
		owned_treasure = Counter(user_data.owned_treasures)

		amount_of_treasure = owned_treasure[treasure_id]

		treasure = all_treasures[treasure_id]

		result_text = ''

		treasure_loc: dict = loc.l(f'items.treasures.{treasure_id}', typecheck=Dict)

		async def update():

			if amount_to_sell == 'all':
				embeds, components = await self.embed_manager(ctx, 'Sell_Treasures', selected_treasure=treasure_id)
			else:
				embeds, components = await self.embed_manager(ctx, 'Sell_Treasures', selected_treasure=treasure_id)

			embeds[0].set_footer(result_text)

			await ctx.edit(embeds=embeds, components=components)

		if amount_of_treasure <= 0:
			result_text = loc.l('shop.traded_fail')
			await update()
			return

		sell_price = 0

		if amount_to_sell == 'all':
			amount = int(amount_of_treasure)

			sell_price = int(amount_of_treasure * treasure['price'] * stock_price)
			owned_treasure[treasure_id] = 0
		else:
			amount = 1

			sell_price = int(treasure['price'] * stock_price)
			owned_treasure[treasure_id] -= 1
		await user_data.update(owned_treasures=owned_treasure)
		result_text = loc.l('shop.traded_sell', item_name=treasure_loc['name'], amount=amount, price=sell_price)

		await user_data.manage_wool(sell_price)

		await update()

	r_treasure_buy = re.compile(r'treasure_buy_(.*)_(.*)')

	@component_callback(r_treasure_buy)
	async def buy_treasure_callback(self, ctx: ComponentContext):
		global daily_shop

		await ctx.defer(edit_origin=True)

		loc = Localization(ctx.locale)

		await self.load_shop()

		user_data: UserData = await UserData(_id=ctx.author.id).fetch()

		match = self.r_treasure_buy.match(ctx.custom_id)

		if not match:
			return

		raw_tid: str = match.group(1)
		if raw_tid not in get_args(TreasureTypes):
			raise ValueError(f"Unknown treasure type: {raw_tid}")
		treasure_id: TreasureTypes = raw_tid  # type:ignore
		amount_to_buy = match.group(2)

		all_treasures = await fetch_treasure()

		treasure = all_treasures[treasure_id]

		result_text = ''

		treasure_price = int(treasure['price'] * daily_shop.stock.price)

		async def update(text: str):
			embeds, components = await self.embed_manager(ctx, 'Treasures', selected_treasure=treasure_id)
			embeds[0].set_footer(text)

			await ctx.edit(embeds=embeds, components=components)

		if user_data.wool < treasure_price:
			return await update(loc.l('shop.traded_fail'))

		current_balance = user_data.wool
		price = 0
		amount = 0

		treasure_loc: dict = loc.l(f'items.treasures.{treasure_id}', typecheck=dict)

		name = treasure_loc['name']

		if amount_to_buy == 'All':

			amount = min(self.max_buy_sell_limit, current_balance // treasure_price)
			price = treasure_price * amount

		else:
			price = int(treasure_price)
			amount = 1

		owned_treasure = Counter(user_data.owned_treasures)

		owned_treasure[treasure_id] = owned_treasure.get(treasure_id, 0) + amount

		await user_data.update(owned_treasures=owned_treasure)
		await user_data.manage_wool(-price)

		return await update(loc.l('shop.traded', item_name=name, amount=int(amount), price=int(price)))

	r_buy_bg = re.compile(r'buy_bg_(.*)_(\d+)')

	@component_callback(r_buy_bg)
	async def buy_bg_callback(self, ctx: ComponentContext):
		loc = Localization(ctx.locale)
		await ctx.defer(edit_origin=True)

		user: UserData = await UserData(_id=ctx.author.id).fetch()

		match = self.r_buy_bg.match(ctx.custom_id)

		if not match:
			return

		bg_id = match.group(1)
		page = int(match.group(2))

		all_bgs = await fetch_background()
		get_background = all_bgs[bg_id]

		owned_backgrounds = user.owned_backgrounds

		embeds, components = await self.embed_manager(ctx, 'Backgrounds', page=page)
		if bg_id in owned_backgrounds:
			embeds[0].set_footer(loc.l('shop.buttons.owned'))
		elif user.wool < get_background['price']:
			embeds[0].set_footer(loc.l('shop.buttons.too_poor'))
		else:
			await owned_backgrounds.append(bg_id)

			embeds[0].description = loc.l(
			    'shop.backgrounds.newly_owned', user_wool=loc.l('shop.user_wool', wool=user.wool)
			)
			await user.manage_wool(-get_background['price'])
			embeds[0].set_footer(loc.l('shop.backgrounds.traded'))
		await ctx.send(embeds=embeds, components=components, ephemeral=True)

	@component_callback('nikogotchi_buy')
	async def buy_nikogotchi_callback(self, ctx: ComponentContext):

		await ctx.defer(edit_origin=True)

		loc = Localization(ctx.locale)

		user_data: UserData = await UserData(_id=ctx.author.id).fetch()
		nikogotchi: Nikogotchi = await Nikogotchi(_id=ctx.author.id).fetch()

		capsule_id = random.choices(range(0, 3), weights=[ 0.40, 0.30, 0.20, 0.10 ], k=1)[0]

		capsules = await fetch_item()
		capsules = capsules['capsules']

		nikogotchi_capsule = Item(**capsules[capsule_id])
		capsule_loc = loc.l(f'items.capsules.{nikogotchi_capsule.id}')

		async def update(result: str):
			embeds, components = await self.embed_manager(ctx, 'capsules')
			embeds[0].set_footer(result)

			await ctx.edit(embeds=embeds, components=components)

		if nikogotchi.status > -1 or nikogotchi.available:
			return await update(loc.l('shop.traded_fail'))

		if user_data.wool < nikogotchi_capsule.cost:
			return await update(loc.l('shop.traded_fail'))

		await nikogotchi.update(available=True, rarity=capsule_id)
		await user_data.manage_wool(-50_000)

		await update(loc.l('shop.nikogotchi.result', amount=50_000, capsule_name=capsule_loc))

	r_buy_object = re.compile(r'buy_([^\d]+)_(\d+)')

	@component_callback(r_buy_object)
	async def buy_pancakes_callback(self, ctx: ComponentContext):

		await ctx.defer(edit_origin=True)

		loc = Localization(ctx.locale)

		user_data: UserData = await UserData(_id=ctx.author.id).fetch()
		nikogotchi_data: Nikogotchi = await Nikogotchi(_id=ctx.author.id).fetch()

		match = self.r_buy_object.match(ctx.custom_id)

		if not match:
			return

		item_category = match.group(1)
		item_id = int(match.group(2))

		result_text = ''

		async def update():

			embeds, components = await self.embed_manager(ctx, item_category)
			embeds[0].set_footer(result_text)

			return await ctx.edit(embeds=embeds, components=components)

		item = await fetch_item()
		item = item['pancakes'][item_id]
		item = Item(**item)

		item_loc: dict = loc.l(
		    f'items.pancakes.{pancake_id_to_emoji_index_please_rename_them_in_db(item.id)}', typecheck=dict
		)

		if user_data.wool < item.cost:
			result_text = loc.l('shop.traded_fail')
			return await update()

		result_text = loc.l('shop.traded', amount=1, item_name=item_loc['name'])

		json_data = asdict(nikogotchi_data)

		await nikogotchi_data.update(**{item.id: json_data[item.id] + 1})

		await user_data.manage_wool(-item.cost)
		await update()

	@component_callback('capsules', 'pancakes', 'Backgrounds', 'Treasures', 'go_back')
	async def main_shop_callbacks(self, ctx: ComponentContext):
		await ctx.defer(edit_origin=True)

		await self.load_shop()

		embeds, components = await self.embed_manager(ctx, ctx.custom_id, page=0)
		await ctx.edit(embeds=embeds, components=components)

	r_page = re.compile(r'page_([^\d]+)_(\d+)')

	@component_callback(r_page)
	async def page_callback(self, ctx: ComponentContext):

		await self.load_shop()

		await ctx.defer(edit_origin=True)

		match = self.r_page.match(ctx.custom_id)

		if not match:
			return

		action = match.group(1)
		bg_page = int(match.group(2))

		bgs = daily_shop.background_stock

		if action == 'prev':
			if bg_page > 0:
				bg_page -= 1
			else:
				bg_page = len(bgs) - 1

		if action == 'next':
			if bg_page < len(bgs) - 1:
				bg_page += 1
			else:
				bg_page = 0

		embeds, components = await self.embed_manager(ctx, 'Backgrounds', page=bg_page)

		await ctx.edit(embeds=embeds, components=components)

	## EMBED MANAGER ---------------------------------------------------------------

	async def embed_manager(self, ctx: SlashContext | ComponentContext, category: str, **kwargs):
		global daily_shop

		await self.load_shop()

		loc = Localization(ctx.locale)

		user_data: UserData = await UserData(_id=ctx.author.id).fetch()

		wool: int = user_data.wool

		stock: str = loc.l('shop.stocks', value=daily_shop.stock.value, price=daily_shop.stock.price)

		user_wool = loc.l('shop.user_wool', wool=user_data.wool)
		magpie_image = EmbedAttachment(
		    'https://cdn.discordapp.com/attachments/1025158352549982299/1176956900928131143/Magpie.webp'
		)

		go_back = Button(style=ButtonStyle.GRAY, custom_id='go_back', label=loc.l('shop.buttons.go_back'))

		b_trade: str = loc.l('shop.buttons.buy')
		b_owned: str = loc.l('shop.buttons.owned')
		b_poor: str = loc.l('shop.buttons.too_poor')
		b_poor_all: str = loc.l('shop.buttons.too_poor_all')
		embeds = []
		components = []
		if category == 'main_shop' or category == 'go_back':

			motds: tuple = loc.l('shop.motds', typecheck=tuple)

			motd = motds[daily_shop.motd]

			embeds.append(
			    Embed(
			        title=loc.l('shop.main_title'),
			        description=loc.l('shop.main', motd=motd, user_wool=user_wool),
			        thumbnail=magpie_image,
			        color=Colors.SHOP
			    )
			)

			buttons = [
			    Button(
			        label=loc.l('shop.nikogotchi.title'),
			        emoji=emojis['icons']["capsule"],
			        style=ButtonStyle.BLURPLE,
			        custom_id='capsules'
			    ),
			    Button(
			        label=loc.l('shop.pancakes.title'),
			        emoji=emojis["pancakes"]['normal'],
			        style=ButtonStyle.BLURPLE,
			        custom_id='pancakes'
			    ),
			    Button(
			        label=loc.l('shop.backgrounds.title'),
			        emoji=emojis['treasures']["card"],
			        style=ButtonStyle.BLURPLE,
			        custom_id='Backgrounds'
			    ),
			    Button(
			        label=loc.l('shop.treasures.buy.title'),
			        emoji=emojis['icons']["inverted_clover"],
			        style=ButtonStyle.BLURPLE,
			        custom_id='Treasures'
			    )
			]
			components = [ActionRow(*buttons)]
		elif category == 'capsules':

			nikogotchi: Nikogotchi = await Nikogotchi(ctx.author.id).fetch()
			capsules: dict = await fetch_item()
			cost = 50_000

			caspule_text = ''
			buttons = []

			for i, capsule in enumerate(capsules['capsules']):

				item = Item(**capsule)

				capsule_loc = loc.l(f'items.capsules.{item.id}')

			button = Button(
			    label=loc.l('shop.buttons.buy'),
			    emoji=PartialEmoji(1147279947086438431),
			    style=ButtonStyle.BLURPLE,
			    custom_id=f'nikogotchi_buy'
			)

			if nikogotchi.available or nikogotchi.status > -1:
				button.disabled = True
				button.style = ButtonStyle.RED
				button.label = b_owned

			if wool < item.cost:
				button.disabled = True
				button.style = ButtonStyle.GRAY
				button.label = b_poor

			buttons.append(button)

			buttons.append(go_back)

			title = loc.l('shop.nikogotchi.title')
			description = loc.l('shop.nikogotchi.main', cost=cost, user_wool=user_wool)

			embeds.append(Embed(title=title, description=description, thumbnail=magpie_image, color=Colors.SHOP))
			components.append(ActionRow(*buttons))
		elif category == 'pancakes':

			pancake_data = await fetch_item()

			nikogotchi_data: Nikogotchi = await Nikogotchi(ctx.author.id).fetch()
			json_data = asdict(nikogotchi_data)

			pancake_text = ''
			buttons: list[Button] = []
			for id_, pancake in enumerate(pancake_data['pancakes']):

				pancake = Item(**pancake)
				pancake_id = pancake_id_to_emoji_index_please_rename_them_in_db(pancake.id)
				owned = json_data[pancake.id]

				amount_owned = loc.l('shop.owned', amount=owned)
				pancake_loc: dict = loc.l(f'items.pancakes.{pancake_id}', typecheck=dict)

				pancake_text += f"{emojis['pancakes'][pancake_id]} **{pancake_loc['name']}** - {emojis['icons']['wool']}{fnum(pancake.cost)} - {amount_owned}\n{pancake_loc['description']}\n"

				button = Button(
				    label=loc.l('shop.buttons.buy'),
				    emoji=emojis['pancakes'][pancake_id],
				    style=ButtonStyle.BLURPLE,
				    custom_id=f'buy_pancakes_{id_}'
				)

				if wool < pancake.cost:
					button.disabled = True
					button.style = ButtonStyle.GRAY
					button.label = b_poor

				buttons.append(button)

			buttons.append(go_back)

			title = loc.l('shop.pancakes.title')
			description = loc.l('shop.pancakes.main', items=pancake_text, user_wool=user_wool)

			embeds.append(Embed(title=title, description=description, thumbnail=magpie_image, color=Colors.SHOP))
			components.append(ActionRow(*buttons))
		elif category == 'Backgrounds':

			bg_page = kwargs['page']
			print(daily_shop)
			background = daily_shop.background_stock[bg_page]
			all_bgs = await fetch_background()
			fetched_background = all_bgs[background]

			user_backgrounds = user_data.owned_backgrounds

			background_name = loc.l(f'items.backgrounds.{background}')
			background_description = loc.l(
			    'shop.backgrounds.main', amount=fetched_background['price'], user_wool=user_wool
			)

			embed = Embed(
			    title=background_name, description=background_description, thumbnail=magpie_image, color=Colors.SHOP
			)
			embeds.append(embed)

			embed.set_image(url=fetched_background["image"])

			buttons = [
			    Button(label='<', style=ButtonStyle.BLURPLE, custom_id=f'page_prev_{bg_page}'),
			    Button(
			        label=loc.l('shop.buttons.buy'),
			        style=ButtonStyle.GREEN,
			        custom_id=f'buy_bg_{background}_{bg_page}'
			    ), go_back,
			    Button(label='>', style=ButtonStyle.BLURPLE, custom_id=f'page_next_{bg_page}')
			]

			buy_button = buttons[1]

			if wool < fetched_background['price']:
				buy_button.disabled = True
				buy_button.style = ButtonStyle.GRAY
				buy_button.label = b_poor

			if background in user_backgrounds:
				embed.description = None
				buy_button.disabled = True
				buy_button.style = ButtonStyle.RED
				buy_button.label = b_owned

			buttons[1] = buy_button
			components.append(ActionRow(*buttons))
		elif category == 'Treasures':

			selected_treasure = kwargs.get('selected_treasure', None)
			selected_treasure_loc: dict = { 'name': '???'}
			buy_price_one = 0
			buy_price_all = 0

			treasure_details = ''

			user_data = await UserData(_id=ctx.author.id).fetch()

			owned = user_data.owned_treasures
			all_treasures = await fetch_treasure()

			if selected_treasure is not None:

				get_selected_treasure = all_treasures[selected_treasure]
				selected_treasure_loc: dict = loc.l(f'items.treasures.{selected_treasure}', typecheck=dict)

				amount_selected = owned.get(selected_treasure, 0)

				buy_price_one = int(get_selected_treasure['price'] * daily_shop.stock.price)

				current_balance = user_data.wool

				amount = 0

				i = 0

				max_items = min(self.max_buy_sell_limit, current_balance // buy_price_one)

				amount = int(max_items)
				buy_price_all = int(max_items * buy_price_one)

				treasure_details = loc.l(
				    'shop.treasures.selection',
				    treasure_icon=emojis['treasures'][selected_treasure],
				    treasure_name=selected_treasure_loc['name'],
				    owned=loc.l('shop.owned', amount=amount_selected),
				    price_one=buy_price_one,
				    price_all=buy_price_all,
				    limit=self.max_buy_sell_limit,
				    amount=amount
				)

			treasure_stock: list[TreasureTypes] = daily_shop.treasure_stock

			buttons: list[Button] = []
			bottom_buttons: list[Button] = []

			user_data = await UserData(_id=ctx.author.id).fetch()

			owned = user_data.owned_treasures

			treasure_list = []
			for treasure in treasure_stock:

				get_treasure = all_treasures[treasure]

				amount_owned = loc.l('shop.owned', amount=owned.get(treasure, 0))
				treasure_loc: dict = loc.l(f'items.treasures.{treasure}', typecheck=dict)

				treasure_list.append(
				    StringSelectOption(
				        label=loc.l(
				            'shop.treasures.buy.option', name=treasure_loc['name'], price=get_treasure['price']
				        ),
				        description=treasure_loc['description'],
				        value=treasure,
				        emoji=emojis['treasures'][treasure]
				    )
				)

			if selected_treasure is not None:

				get_selected_treasure = all_treasures[selected_treasure]

				button = Button(
				    label=loc.l('shop.buttons.buy'),
				    emoji=emojis['treasures'][selected_treasure],
				    style=ButtonStyle.BLURPLE,
				    custom_id=f'treasure_buy_{selected_treasure}_One'
				)

				button_all = Button(
				    label=loc.l('shop.buttons.buy_all'),
				    emoji=emojis['treasures'][selected_treasure],
				    style=ButtonStyle.BLURPLE,
				    custom_id=f'treasure_buy_{selected_treasure}_All'
				)

				if wool < buy_price_one:
					button.disabled = True
					button.style = ButtonStyle.GRAY
					button.label = b_poor

					button_all.disabled = True
					button_all.style = ButtonStyle.GRAY
					button_all.label = b_poor

				buttons.append(button)
				buttons.append(button_all)

			buttons.append(
			    Button(
			        label=loc.l('shop.treasures.sell.title'), style=ButtonStyle.GREEN, custom_id='sell_treasure_menu'
			    )
			)

			buttons.append(go_back)

			title = loc.l('shop.treasures.buy.title')
			description = loc.l(
			    'shop.treasures.buy.message',
			    stock_market=stock,
			    selected_treasure=treasure_details,
			    user_wool=user_wool
			)

			embeds.append(Embed(title=title, description=description, thumbnail=magpie_image, color=Colors.SHOP))

			select_menu = None

			if len(treasure_list) > 0:
				select_menu = StringSelectMenu(
				    *treasure_list,
				    placeholder=loc.l('shop.treasures.buy.placeholder'),
				    custom_id=f'select_treasure',
				)
			else:
				select_menu = StringSelectMenu(
				    '💥💥💥💥💥💥💥💥💥💥💥💥',
				    placeholder=loc.l('shop.treasures.cannot_sell'),
				    custom_id=f'select_treasure',
				    disabled=True
				)

			components = [ActionRow(select_menu), ActionRow(*buttons)]
		elif category == 'Sell_Treasures':
			go_back = Button(label=loc.l('shop.buttons.go_back'), style=ButtonStyle.GRAY, custom_id='Treasures')
			selected_treasure = kwargs['selected_treasure']
			selected_treasure_loc: dict = { 'name': '???'}
			sell_price_one = 0
			sell_price_all = 0

			treasure_details = ''

			user_data = await UserData(_id=ctx.author.id).fetch()

			owned = user_data.owned_treasures
			all_treasures = await fetch_treasure()

			if selected_treasure is not None:

				get_selected_treasure = all_treasures[selected_treasure]
				selected_treasure_loc: dict = loc.l(f'items.treasures.{selected_treasure}', typecheck=dict)

				sell_price_one = int(get_selected_treasure['price'] * daily_shop.stock.price)
				sell_price_all = int(get_selected_treasure['price'] * daily_shop.stock.price * owned[selected_treasure])

				amount_selected = int(owned.get(selected_treasure, 0))

				if amount_selected > 0:

					treasure_details = loc.l(
					    'shop.treasures.selection',
					    treasure_icon=emojis['treasures'][selected_treasure],
					    treasure_name=selected_treasure_loc['name'],
					    owned=loc.l('shop.owned', amount=amount_selected),
					    price_one=sell_price_one,
					    price_all=sell_price_all,
					    amount=amount_selected
					)

			treasure_selection = []

			for treasure_nid, amount in owned.items():

				if amount <= 0:
					continue
				treasure = all_treasures[treasure_nid]

				treasure_loc = loc.l(f'items.treasures.{treasure_nid}', typecheck=dict)

				treasure_selection.append(
				    StringSelectOption(
				        label=f'{treasure_loc["name"]} (x{amount})',
				        value=treasure_nid,
				        description=treasure_loc['description'],
				        emoji=emojis['treasures'][treasure_nid],
				    )
				)

			selection_description = ''

			buttons = []

			if selected_treasure is not None:
				treasure_id = selected_treasure

				buttons = [
				    Button(
				        label=loc.l('shop.buttons.sell'),
				        custom_id=f'treasure_sell_{treasure_id}_one',
				        style=ButtonStyle.GREEN
				    ),
				    Button(
				        label=loc.l('shop.buttons.sell_all'),
				        custom_id=f'treasure_sell_{treasure_id}_all',
				        style=ButtonStyle.GREEN
				    )
				]
			else:
				treasure_id = 0

			buttons.append(go_back)

			embeds.append(
			    Embed(
			        title=loc.l('shop.treasures.sell.title'),
			        description=loc.l(
			            'shop.treasures.sell.message',
			            stock_market=stock,
			            selected_treasure=treasure_details,
			            user_wool=user_wool
			        ),
			        thumbnail=magpie_image,
			        color=Colors.SHOP
			    )
			)

			select_menu = None

			if len(treasure_selection) > 0:
				select_menu = StringSelectMenu(
				    *treasure_selection,
				    placeholder=loc.l('shop.treasures.sell.placeholder'),
				    custom_id=f'select_treasure_sell',
				)
			else:
				select_menu = StringSelectMenu(
				    '💥💥💥💥💥💥💥💥💥💥💥💥',
				    placeholder=loc.l('shop.treasures.sell.no_treasures'),
				    custom_id=f'select_treasure_sell',
				    disabled=True
				)

			components = [ActionRow(select_menu), ActionRow(*buttons)]

		return (embeds, components)
	@slash_command(description="Open the Shop")
	@integration_types(guild=True, user=True)
	@contexts(bot_dm=True)
	async def shop(self, ctx: SlashContext):

		await ctx.defer(ephemeral=True)

		await self.load_shop()

		embeds, button = await self.embed_manager(ctx, 'main_shop')

		await ctx.send(embeds=embeds, components=button)
