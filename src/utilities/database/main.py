import yaml
from interactions import Snowflake
from utilities.config import get_config
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any, Generic, Iterable, get_origin, get_type_hints, TypeVar, overload
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
			assert field_type is not None

			if name in [ "_id", "_parent", "_parent_field"]:
				continue

			if isinstance(value, dict):
				if get_origin(field_type) == DBDynamicDict:
					setattr(self, name, field_type(_parent=self, _parent_field=name, **value))
				else:
					setattr(self, name, init_things(field_type(_parent=self, _parent_field=name, **value)))
			elif isinstance(value, list):
				setattr(self, name, field_type(default=value, _parent=self, _parent_field=name))
	return self


TCollection = TypeVar('TCollection', bound='Collection')


@dataclass
class Collection:
	_id: str | Snowflake

	async def update(self, **kwargs):
		'''Update the current collection with the given kwargs.'''
		updated_data = await update_in_database(self, **kwargs)
		# The new overloads for to_dict will correctly infer a dict type here
		for k, v in to_dict(updated_data).items():
			setattr(self, k, v)
		return init_things(updated_data)

	async def fetch(self: TCollection) -> TCollection:
		'''Fetch the current collection using id.'''
		self._id = str(self._id)

		db = await get_database()

		result = await db.get_collection(self.__class__.__name__).find_one({ '_id': str(self._id)})

		if result is None:
			await new_entry(self)
			return await self.fetch()
		return self.__class__(**result)

	def __post_init__(self):
		init_things(self)

	async def update_array(self, field: str, operator: str, value: Any):
		db = await get_database()
		await db.get_collection(self.__class__.__name__
		                       ).update_one({ '_id': str(self._id)}, { operator: {
		                           field: value
		                       }})

	async def increment_key(self, key: str, by: int | float = 1):

		value = getattr(self, key, 0)

		if isinstance(value, float):
			by = float(by)
		# could use self.key += by maybe, instead of returning a whole new objec (.update does that)
		return await self.update(**{ key: value + by})


class DBDict(dict):
	_parent: Collection | None
	_parent_field: str | None

	def __init__(self, *args, _parent: Collection | None = None, _parent_field: str | None = None, **kwargs):
		super().__init__(*args, **kwargs)

		self._parent = _parent
		self._parent_field = _parent_field

	def __repr__(self):
		return f"DB{super().__repr__()}"

	async def update(self, **kwargs):
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")

		current_state = to_dict(self)
		updated_state = { **current_state, **kwargs }
		update_fields = {self._parent_field: updated_state}
		await self._parent.update(**update_fields)

		super().update(kwargs)

	async def increment_key(self, key: str, by: int | float = 1):
		value = self.get(key, 0)
		if isinstance(value, float):
			by = float(by)
		await self.update(**{ key: value + by})

	async def update_array(self, field: str, operator: str, value: Any):
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")
		await self._parent.update_array(f"{self._parent_field}.{field}", operator, value)

	async def fetch(self) -> Collection:
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested fetch.")
		# This might need adjustment based on what _parent.fetch() returns
		parent_data = await self._parent.fetch()
		return parent_data.__getattribute__(self._parent_field)


TItem = TypeVar("TItem")


class DBList(list, Generic[TItem]):
	_parent: Collection | None
	_parent_field: str | None

	def __init__(
	    self,
	    default: Iterable[TItem] | None = None,
	    _parent: Collection | None = None,
	    _parent_field: str | None = None
	):
		super().__init__(default or [])

		self._parent = _parent
		self._parent_field = _parent_field

	def __repr__(self):
		return f"DB{super().__repr__()}"

	async def append(self, item: TItem) -> None:
		"""Append object to the end of the list, and update self in the database"""
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")

		await self._parent.update_array(self._parent_field, '$push', item)
		super().append(item)

	async def remove(self, item: TItem) -> None:
		"""Remove first occurrence of value, and update self in the database"""
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")

		await self._parent.update_array(self._parent_field, '$pull', item)
		super().remove(item)

	async def extend(self, iterable: Iterable[TItem]) -> None:
		"""Extend the list by appending items from the iterable, and update self in the database"""
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")

		items_to_add = list(iterable)
		if not items_to_add:
			return

		# MongoDB's $push with $each expects a list of items
		await self._parent.update_array(self._parent_field, '$push', { '$each': items_to_add})
		super().extend(items_to_add)

	async def clear(self) -> None:
		"""Clear the list, and update self in the database"""
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")

		await self._parent.update_array(self._parent_field, '$set', [])
		super().clear()


TKey = TypeVar("TKey")
TValue = TypeVar("TValue")


class DBDynamicDict(dict, Generic[TKey, TValue]):
	_parent: Collection | None
	_parent_field: str | None

	def __init__(self, *args: Any, _parent: Collection | None = None, _parent_field: str | None = None, **kwargs: Any):
		super().__init__(*args, **kwargs)

		self._parent = _parent
		self._parent_field = _parent_field

	async def __setitem__(self, key: TKey, value: Any) -> None:
		if self._parent is not None and self._parent_field is not None:
			updated_dict_state = dict(self)
			updated_dict_state[key] = value

			update_fields = {self._parent_field: updated_dict_state}
			await self._parent.update(**update_fields)

		super().__setitem__(key, value)

	async def update(self, *args: Any, **kwargs: Any) -> None:
		if self._parent is None or self._parent_field is None:
			raise Exception("Parent not set for nested update.")

		updated_dict_state = dict(self)
		updated_dict_state.update(*args, **kwargs)

		update_fields = {self._parent_field: updated_dict_state}
		await self._parent.update(**update_fields)

		super().update(*args, **kwargs)

	async def increment_key(self, key: TKey, by: int | float = 1) -> None:
		current_value = self.get(key, 0)

		if not isinstance(current_value, (int, float)):
			current_value = 0

		await self.__setitem__(key, current_value + by)

	def __repr__(self) -> str:
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


async def get_database():

	if connection is None:
		await connect_to_db()
	assert connection != None

	return connection.get_database('TheWorldMachine')


async def new_entry(collection: Collection):

	db = await get_database()

	await db.get_collection(collection.__class__.__name__
	                       ).update_one({ '_id': str(collection._id)}, { '$set': to_dict(collection)}, upsert=True)


async def update_in_database(collection: TCollection, **kwargs) -> TCollection:
	db = await get_database()
	existing_data = to_dict(collection)
	updated_data = { **existing_data, **kwargs }  # pyright: ignore[reportGeneralTypeIssues]
	await db.get_collection(collection.__class__.__name__
	                       ).update_one({ '_id': str(collection._id)}, { '$set': updated_data}, upsert=True)
	return collection.__class__(**updated_data)


async def fetch_items():
	db = await get_database()

	data = await db.get_collection('ItemData').find_one({ "access": 'ItemData'})

	return data


async def update_shop(data: dict):
	db = await get_database()

	await db.get_collection('ItemData').update_one({ "access": 'ItemData'}, { "$set": { "shop": data}})


Serializable = dict[str, "Serializable"] | list["Serializable"] | tuple["Serializable",
                                                                        ...] | str | int | float | bool | None

T_Primitive = TypeVar("T_Primitive", str, int, float, bool)


@overload
def to_dict(obj: "Collection") -> dict[str, Serializable]:
	...


@overload
def to_dict(obj: DBDict) -> dict[str, Serializable]:
	...


@overload
def to_dict(obj: DBDynamicDict) -> dict[str, Serializable]:
	...


@overload
def to_dict(obj: dict[Any, Any]) -> dict[str, Serializable]:
	...


@overload
def to_dict(obj: DBList) -> list[Serializable]:
	...


@overload
def to_dict(obj: list[Any]) -> list[Serializable]:
	...


@overload
def to_dict(obj: tuple[Any, ...]) -> tuple[Serializable, ...]:
	...


@overload
def to_dict(obj: T_Primitive) -> T_Primitive:
	...


@overload
def to_dict(obj: None) -> None:
	...


def to_dict(obj: Any) -> Serializable:
	"""
    Recursively converts a Python object into a serializable dictionary.
    """
	if is_dataclass(obj):
		result: dict[str, Serializable] = {}
		for f in fields(obj):
			if f.name in [ "_parent", "_parent_field", "_field_name"]:
				continue
			value = getattr(obj, f.name)
			result[f.name] = to_dict(value)
		return result
	elif isinstance(obj, (DBList, list)):
		return [to_dict(x) for x in obj]
	elif isinstance(obj, tuple):
		return tuple(to_dict(x) for x in obj)
	elif isinstance(obj, (DBDict, DBDynamicDict, dict)):
		return {str(k): to_dict(v) for k, v in obj.items()}
	else:
		return obj


for dc in (yaml.Dumper, yaml.SafeDumper):
	yaml.add_representer(DBList, lambda dumper, data: dumper.represent_list(list(data)), Dumper=dc)
	yaml.add_representer(DBDict, lambda dumper, data: dumper.represent_dict(to_dict(data)), Dumper=dc)
	yaml.add_representer(DBDynamicDict, lambda dumper, data: dumper.represent_dict(to_dict(data)), Dumper=dc)
