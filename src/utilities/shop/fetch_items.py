from collections import OrderedDict
from utilities.database.main import fetch_items
import asyncio


async def fetch_item():

	item_data = await fetch_items()

	return item_data['items']


async def fetch_treasure():

	item_data = await fetch_items()

	return item_data['treasures']


async def fetch_background():

	item_data = await fetch_items()

	return item_data['backgrounds']


async def fetch_badge():

	item_data = await fetch_items()

	item_data = item_data['badges']

	return OrderedDict(sorted(item_data.items(), key=lambda x: x[1]['id']))
