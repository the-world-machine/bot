from enum import Enum
from dataclasses import dataclass
import json

# ! DEPRECATED. ALL NIKOGOTCHI DATA IS NOW ON THE DATABASE THIS IS JUST FOR RECOVERY !

# Create nikogotchi.json in the root directory and run the script. It should create json data necessary to implement in MongoDB.

class Rarity(Enum):
    BLUE = 0
    GREEN = 1
    RED = 2
    YELLOW = 3

@dataclass
class NikogotchiInformation:
    name: str
    emoji: int
    rarity: Rarity

nikogotchi_list = [
    NikogotchiInformation(
        "Prophet Bot",
        '1147182670892253247',
        Rarity.BLUE
    ),
    NikogotchiInformation(
        "Silver",
        '1147176557467672616',
        Rarity.BLUE
    ),
    NikogotchiInformation(
        "Alula",
        '1147176544259801189',
        Rarity.GREEN
    ),
    NikogotchiInformation(
        "Calamus",
        '1147176547464253471',
        Rarity.GREEN
    ),
    NikogotchiInformation(
        "Magpie",
        '1147176551285272597',
        Rarity.GREEN
    ),
    NikogotchiInformation(
        "Lamplighter",
        '1147182659798319175',
        Rarity.RED
    ),
    NikogotchiInformation(
        "Watcher",
        '1146965094845136946',
        Rarity.RED
    ),
    NikogotchiInformation(
        "Ling",
        '1147183240063500348',
        Rarity.RED
    ),
    NikogotchiInformation(
        "Kelvin",
        '1146967527512100925',
        Rarity.RED
    ),
    NikogotchiInformation(
        "Kip",
        '1147182658540032051',
        Rarity.RED
    ),
    NikogotchiInformation(
        "Penguin",
        '1147182669562654851',
        Rarity.RED
    ),
    NikogotchiInformation(
        "George",
        '1147183958279323759',
        Rarity.RED
    ),
    NikogotchiInformation(
        "Rue",
        '1147182674964906077',
        Rarity.YELLOW
    ),
    NikogotchiInformation(
        "Prototype",
        '1147182673673076828',
        Rarity.YELLOW
    ),
    NikogotchiInformation(
        "Cedric",
        '1147182656191205396',
        Rarity.YELLOW
    ),
    NikogotchiInformation(
        "The World Machine",
        '1147182676021878887',
        Rarity.YELLOW
    ),
    NikogotchiInformation(
        "Niko",
        '1147176553655058492',
        Rarity.YELLOW
    )
]

def serialize_data(obj):
    return obj.name

json_data = json.dumps([obj.__dict__ for obj in nikogotchi_list], default=serialize_data, indent=4)

with open('nikogotchi.json', 'w') as f:
    f.write(json_data)