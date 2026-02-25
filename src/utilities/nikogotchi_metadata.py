import random
from dataclasses import dataclass
from enum import Enum

from utilities.database.main import get_database


class Rarity(Enum):
	BLUE = 0
	GREEN = 1
	RED = 2
	YELLOW = 3
	PURPLE = 4


@dataclass()
class NikogotchiMetadata:
	# Nikogotchi Information
	name: str
	rarity: Rarity
	image_url: str


def convert_to_class(data: dict, nid: str):
	return NikogotchiMetadata(nid, Rarity(data["rarity"]), data["image"])


async def fetch_nikogotchi_metadata(nid: str) -> NikogotchiMetadata | None:
	db = await get_database()

	result = await db.get_collection("NikogotchiFeatures").find_one(
		{"key": "NikogotchiFeatures"}, {"_id": 0, "nikogotchi": 1}
	)

	# Cast the result to the expected structure
	nikogotchi_data: dict[str, NikogotchiMetadata] = result["nikogotchi"] if result else {}
	nikogotchi_info = nikogotchi_data.get(nid)
	if nikogotchi_info == None or type(nikogotchi_info) is not dict:
		return None
	return convert_to_class(nikogotchi_info, nid)


async def pick_random_nikogotchi(rarity: int):
	db = await get_database()

	result = await db.get_collection("NikogotchiFeatures").find_one(
		{"key": "NikogotchiFeatures"}, {"_id": 0, "nikogotchi": 1}
	)

	nikogotchi_info = result["nikogotchi"] if result else {}

	candidates = []

	keys = list(nikogotchi_info.keys())
	for key in keys:
		if nikogotchi_info[key]["rarity"] == rarity:
			candidates.append(key)

	choice = random.choice(candidates)

	return convert_to_class(nikogotchi_info[choice], choice)
