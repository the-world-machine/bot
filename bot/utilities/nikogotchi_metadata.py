from enum import Enum
from dataclasses import dataclass
from database import get_database
import random
import json
import asyncio

class Rarity(Enum):
    BLUE = 0
    GREEN = 1
    RED = 2
    YELLOW = 3

@dataclass()
class NikogotchiMetadata:
    # Nikogotchi Information
    name: str
    rarity: Rarity
    image_url: str

def convert_to_class(data: dict, nid: str):
    return NikogotchiMetadata(
        nid,
        Rarity(data['rarity']),
        data['image']
    )

async def fetch_nikogotchi_metadata(nid: str):
    db = get_database()
    
    result = await db.get_collection('NikogotchiFeatures').find_one({'key': 'NikogotchiFeatures'})
    
    nikogotchi_info = result['nikogotchi'].get(nid, None)
    
    if nikogotchi_info is None:
        return
    
    return convert_to_class(nikogotchi_info, nid)
    
    
async def pick_random_nikogotchi(rarity: int):
    db = get_database()
    
    result = await db.get_collection('NikogotchiFeatures').find_one({'key': 'NikogotchiFeatures'})
    
    nikogotchi_info = result['nikogotchi']
    
    candidates = []
    
    keys = list(nikogotchi_info.keys())
    for key in keys:
        if nikogotchi_info[key]['rarity'] == rarity:
            candidates.append(key)
    
    choice = random.choice(candidates)
    
    return convert_to_class(nikogotchi_info[choice], choice)