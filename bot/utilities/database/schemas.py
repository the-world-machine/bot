import random
from datetime import datetime
from dataclasses import asdict, dataclass, field
from utilities.database.main import DBDict, DBDynamicDict, DBList, Collection


"""{
  "_id": "1142872664323666020",
  "allow_ask": true,
  "anonymous": false,
  "blocked_servers": [],
  "language": "english",
  "transmit_channel": null,
			blocklist
  "transmit_images": true,
  "transmittable_servers": {
    "1017479547664482444": "TWM Development",
    "1228802704181301381": "Cult of Sinkeme"
  },
  "welcome_message": ""
}"""

@dataclass
class TransmitConfig(DBDict):
	disabled: bool = False
	channel_id: str | None = None
	anonymous: bool = False
	allow_images: bool = True
	blocked_servers: DBList[str] = field(default_factory=list)
	known_servers: DBList[str] = field(default_factory=list)

@dataclass
class WelcomeConfig(DBDict):
	disabled: bool | None = True
	ping: bool = False
	channel_id: str = None
	#character: str = None
	#face: str = None
	#animated: bool = True
	message: str = ""


@dataclass
class ServerData(Collection):
	transmissions: TransmitConfig = field(default_factory=dict)
	welcome: WelcomeConfig = field(default_factory=dict)


@dataclass
class UserData(Collection):
	wool: int = 0
	suns: int = 0
	equipped_bg: str = 'Default'
	profile_description: str = 'Hello World!'
	badge_notifications: bool = True
	owned_treasures: DBDynamicDict[str, int] = field(default_factory=lambda: { 'journal': 5})
	owned_backgrounds: DBList[str] = field(
	    default_factory=lambda: [ 'Default', 'Blue', 'Red', 'Yellow', 'Green', 'Pink']
	)
	owned_badges: DBList[str] = field(default_factory=list)
	ask_limit: int = 14
	last_asked: datetime = field(default_factory=lambda: datetime(2000, 1, 1, 0, 0, 0))
	daily_wool_timestamp: datetime = field(default_factory=lambda: datetime(2000, 1, 1, 0, 0, 0))
	daily_sun_timestamp: datetime = field(default_factory=lambda: datetime(2000, 1, 1, 0, 0, 0))
	times_asked: int = 0
	times_transmitted: int = 0
	times_shattered: int = 0
	translation_language: str = 'english'

	async def increment_value(self, key: str, amount: int = 1):
		'Increment a value within the UserData object.'
		value = asdict(self)[key]

		if type(value) == float:
			int(value)

		return await self.update(**{ key: value + amount})

	async def manage_wool(self, amount: int):

		wool = self.wool + amount

		if wool <= 0:
			wool = 0

		if wool >= 999999999999999999:
			wool = 999999999999999999

		return await self.update(wool=int(wool))



@dataclass
class NikogotchiData(Collection):
	last_interacted: datetime = field(default_factory=lambda: datetime(2000, 1, 1, 0, 0, 0))
	hatched: datetime = field(default_factory=lambda: datetime(2000, 1, 1, 0, 0, 0))
	data: DBDynamicDict[str, int] = field(default_factory=dict)
	nikogotchi_available: bool = False
	rarity: int = 0
	pancakes: int = 5
	golden_pancakes: int = 1
	glitched_pancakes: int = 0

@dataclass
class StatUpdate:
	icon: str
	old_value: int
	new_value: int
@dataclass
class Nikogotchi(Collection):
	available: bool = False
	hatched: datetime = field(default_factory=lambda: datetime.now())
	last_interacted: datetime = field(default_factory=lambda: datetime.now())
	started_finding_treasure_at: datetime = field(default_factory=lambda: datetime.now())
	status: int = -1

	rarity: int = 0
	pancakes: int = 5
	golden_pancakes: int = 1
	glitched_pancakes: int = 0

	level: int = 0
	health: int = 50
	energy: int = 5
	hunger: int = 50
	cleanliness: int = 50
	happiness: int = 50

	attack: int = 5
	defense: int = 2

	max_health: int = 50
	max_hunger: int = 50
	max_cleanliness: int = 50
	max_happiness: int = 50

	nid: str = '?'
	name: str = 'NONAME'

	async def level_up(self, amount: int) -> list[StatUpdate]:

		level = self.level + amount

		stats: list[StatUpdate] = []

		algorithm = int(amount * 5 * random.uniform(0.8, 1.4))
		stats.append(StatUpdate("❤️", int(self.max_health), int(self.max_health) + int(algorithm)))
		self.max_health += algorithm

		algorithm = int(amount * 5 * random.uniform(0.8, 1.4))
		stats.append(StatUpdate("🍴", int(self.max_hunger), int(self.max_hunger) + int(algorithm)))
		self.max_hunger += algorithm

		algorithm = int(amount * 5 * random.uniform(0.8, 1.4))
		stats.append(StatUpdate(
		    "🫂",
		    int(self.max_happiness),
		    int(self.max_happiness) + int(algorithm),
		))
		self.max_happiness += algorithm

		algorithm = int(amount * 5 * random.uniform(0.8, 1.4))
		stats.append(StatUpdate("🧽", int(self.max_cleanliness), int(self.max_cleanliness) + int(algorithm)))
		self.max_cleanliness += algorithm

		algorithm = int(amount * 2 * random.uniform(0.8, 1.4))
		stats.append(StatUpdate("🗡️", int(self.attack), int(self.attack) + int(algorithm)))
		self.attack += algorithm

		algorithm = int(amount * 2 * random.uniform(0.8, 1.4))
		stats.append(StatUpdate("🛡️", int(self.defense), int(self.defense) + int(algorithm)))
		self.defense += algorithm

		self.level = level

		self.health = self.max_health
		self.hunger = self.max_hunger
		self.happiness = self.max_happiness
		self.cleanliness = self.max_cleanliness

		await self.update(**asdict(self))

		return stats
