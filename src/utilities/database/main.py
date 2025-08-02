import yaml
from interactions import Snowflake
from utilities.config import get_config
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any, Generic, get_type_hints, TypeVar
from dataclasses import dataclass, fields, is_dataclass, InitVar
if get_config("database.dns-fix", typecheck=bool, ignore_None=True):
	import dns.resolver
	dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
	dns.resolver.default_resolver.nameservers = ['8.8.8.8']
connection_uri = get_config('database.uri')


def init_things(self):
	type_hints = get_type_hints(self.__class__)
	if is_dataclass(self):
		for field_info in fields(self):
			value = getattr(self, field_info.name)
			name = field_info.name

			field_type = type_hints.get(name)

			if name in [ "_id", "_parent", "_parent_field"]:
				continue

			if isinstance(value, dict):
				if isinstance(field_type, DBDynamicDict):
					setattr(self, name, field_type(_parent=self, _parent_field=name, **value))
				else:
					setattr(self, name, init_things(field_type(_parent=self, _parent_field=name, **value)))
			elif isinstance(value, list):
				setattr(self, name, field_type(default=value, _parent=self, _parent_field=name))
	return self


TCollection = TypeVar('T', bound='Collection')


@dataclass
class Collection:
	_id: str | Snowflake

	async def update(self, **kwargs):
		'''Update the current collection with the given kwargs.'''
		updated_data = await update_in_database(self, **kwargs)
		for k, v in to_dict(updated_data).items():
			setattr(self, k, v)
		return init_things(updated_data)

	async def fetch(self: TCollection) -> TCollection:
		'''Fetch the current collection using id.'''
		self._id = str(self._id)

		db = get_database()

		result = await db.get_collection(self.__class__.__name__).find_one({ '_id': str(self._id)})

		if result is None:
			await new_entry(self)
			return await self.fetch()
		return self.__class__(**result)

	def __post_init__(self):
		init_things(self)

	async def update_array(self, field: str, operator: str, value: Any):
		db = get_database()
		await db.get_collection(self.__class__.__name__
		                       ).update_one({ '_id': str(self._id)}, { operator: {
		                           field: value
		                       }})

	async def increment_key(self, key: str, by: int = 1):

		value = getattr(self, key, 0)

		if isinstance(value, float):
			by = float(by)
		# could use self.key += by maybe, instead of returning a whole new objec (.update does that)
		return await self.update(**{ key: value + by})


@dataclass
class DBDict(dict):
	_parent: InitVar[Collection] = None
	_parent_field: InitVar[str] = None

	def __post_init__(self, _parent=None, _parent_field=None):
		self._parent = _parent
		self._parent_field = _parent_field

	def __repr__(self):
		return f"DB{super().__repr__()}"

	async def update(self, **kwargs):
		if self._parent is None:
			raise Exception("Parent not set for nested update.")

		current_state = to_dict(self)
		updated_state = { **current_state, **kwargs }

		update_fields = {self._parent_field: updated_state}
		updated_parent = await self._parent.update(**update_fields)

		for k, v in update_fields.items():
			setattr(self, k, v)

	async def increment_key(self, key: str, by: int = 1):

		value = self.get(key, 0)

		if isinstance(value, float):
			by = float(by)

		return await self.update(**{ key: value + by})

	async def update_array(self, field: str, operator: str, value: Any):
		if self._parent is None:
			raise Exception("Parent not set for nested update.")
		await self._parent.update_array(f"{self._parent_field}.{field}", operator, value)

	async def fetch(self) -> TCollection:
		return await self._parent.fetch()[self._parent_field]


class DBList(list):
	_parent: InitVar[TCollection] = None
	_parent_field: InitVar[str] = None

	def __init__(self, default=None, _parent=None, _parent_field=None):
		super().__init__(default or [])
		self._parent = _parent
		self._parent_field = _parent_field

	def __repr__(self):
		return f"DB{super().__repr__()}"

	async def append(self, item) -> None:
		"""Append object to the end of the list, and update self in the database"""

		await self._parent.update_array(self._parent_field, '$push', { '$each': [item]})
		super().append(item)

	async def remove(self, item) -> None:
		"""Remove first occurrence of value, and update self in the database"""
		await self._parent.update_array(self._parent_field, '$pull', item)
		super().remove(item)

	async def extend(self, iterable) -> None:
		"""Extend the list by appending items from the iterable, and update self in the database"""
		await self._parent.update_array(self._parent_field, '$push', { '$each': iterable})
		super().extend(iterable)

	async def clear(self) -> None:
		"""Clear the list, and update self in the database"""
		await self._parent.update_array(self._parent_field, '$set', [])
		super().clear()


K = TypeVar('K')
V = TypeVar('V')


class DBDynamicDict(dict[K, V], Generic[K, V]):
	_parent: InitVar[Collection] = None
	_parent_field: InitVar[str] = None

	def __init__(self, *args, _parent=None, _parent_field=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._parent = _parent
		self._parent_field = _parent_field

	async def __setitem__(self, key, value):
		if self._parent is not None:
			update_fields = {self._parent_field: dict(self, **{ key: value})}
			await self._parent.update(**update_fields)
		super().__setitem__(key, value)

	async def update(self, **kwargs):
		if self._parent is None:
			raise Exception("Parent not set for nested update.")

		update_fields = {self._parent_field: dict(self, **kwargs)}
		await self._parent.update(**update_fields)

		super().update(**kwargs)

	async def increment_key(self, key: str, by: int = 1):

		value = self.get(key, 0)

		if isinstance(value, float):
			by = float(by)

		return await self.update(**{ key: value + by})

	def __repr__(self):
		return f"DBD{super().__repr__()}"


connection = None


async def connect_to_db():
	global connection
	if connection is not None:
		return

	connection = AsyncIOMotorClient(connection_uri, server_api=ServerApi('1'))
	try:
		await connection.admin.command('ping')
		print('Database Connected')
	except Exception as e:
		print(f'Failed to connect to database: {e}')


def get_database():

	if connection is None:
		connect_to_db()

	return connection.get_database('TheWorldMachine')


async def new_entry(collection: Collection):

	db = get_database()

	await db.get_collection(collection.__class__.__name__
	                       ).update_one({ '_id': str(collection._id)}, { '$set': to_dict(collection)}, upsert=True)


async def update_in_database(collection: TCollection, **kwargs) -> TCollection:
	db = get_database()
	existing_data = to_dict(collection)
	updated_data = { **existing_data, **kwargs }  # pyright: ignore[reportGeneralTypeIssues]
	await db.get_collection(collection.__class__.__name__
	                       ).update_one({ '_id': str(collection._id)}, { '$set': updated_data}, upsert=True)
	return collection.__class__(**updated_data)


async def fetch_items():
	db = get_database()

	data = await db.get_collection('ItemData').find_one({ "access": 'ItemData'})

	return data


async def update_shop(data: dict):
	db = get_database()

	await db.get_collection('ItemData').update_one({ "access": 'ItemData'}, { "$set": { "shop": data}})


def to_dict(obj):
	if is_dataclass(obj):
		result = {}
		for f in fields(obj):
			if f.name in [ "_parent", "_parent_field", "_field_name"]:
				continue
			value = getattr(obj, f.name)
			result[f.name] = to_dict(value)
		return result
	elif isinstance(obj, (DBList, list, tuple)):
		return type(obj)(to_dict(x) for x in obj)
	elif isinstance(obj, (DBDict, DBDynamicDict, dict)):
		return { k: to_dict(v) for k, v in obj.items() }
	else:
		return obj


for dc in (yaml.Dumper, yaml.SafeDumper):
	yaml.add_representer(DBList, lambda dumper, data: dumper.represent_list(list(data)), Dumper=dc)
	yaml.add_representer(DBDict, lambda dumper, data: dumper.represent_dict(to_dict(data)), Dumper=dc)
	yaml.add_representer(DBDynamicDict, lambda dumper, data: dumper.represent_dict(to_dict(data)), Dumper=dc)
