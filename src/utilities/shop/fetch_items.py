from collections import OrderedDict
from utilities.database.main import fetch_items


async def fetch_item():

	item_data = await fetch_items()
	assert item_data is not None
	return item_data['items']


async def fetch_treasure():

	item_data = await fetch_items()
	assert item_data is not None
	return item_data['treasures']


async def fetch_background():

	item_data = await fetch_items()
	assert item_data is not None
	return item_data['backgrounds']


async def fetch_badge():

	item_data = await fetch_items()
	assert item_data is not None
	item_data = item_data['badges']

	return OrderedDict(sorted(item_data.items(), key=lambda x: x[1]['id']))
