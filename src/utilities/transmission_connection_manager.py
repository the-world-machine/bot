from typing import Union


class Connection:

	def __init__(self, server_id, channel_id):
		self.server_id = server_id
		self.channel_id = channel_id
		self.characters = [
		    {
		        "id": 0,
		        "Image": 1019605517695463484,
		        "Name": "Niko"
		    },
		    {
		        "id": 0,
		        "Image": 1071085652327813212,
		        "Name": "Alula"
		    },
		    {
		        "id": 0,
		        "Image": 1071085682132529294,
		        "Name": "Calamus"
		    },
		    {
		        "id": 0,
		        "Image": 1071085718975283310,
		        "Name": "Lamplighter"
		    },
		    {
		        "id": 0,
		        "Image": 1027240024992927814,
		        "Name": "Kip"
		    },
		    {
		        "id": 0,
		        "Image": 1090982149659836466,
		        "Name": "Ling"
		    },
		    {
		        "id": 0,
		        "Image": 1023573456664662066,
		        "Name": "The World Machine"
		    },
		]


class Transmission:

	def __init__(self, a: Connection, b: Union[Connection, None]):
		self.connection_a = a
		self.connection_b = b


transmissions: list[Transmission] = []


def create_connection(server_id, channel_id):
	connection = Connection(server_id, channel_id)
	transmissions.append(Transmission(connection, None))


def remove_connection(server_id):
	for transmission in transmissions:
		if transmission.connection_a:
			if transmission.connection_a.server_id == server_id:
				transmissions.remove(transmission)

		if transmission.connection_b:
			if transmission.connection_b.server_id == server_id:
				transmissions.remove(transmission)


def connect_to_transmission(server_id, channel_id):
	for transmission in transmissions:
		if transmission.connection_b is None:
			transmission.connection_b = Connection(server_id, channel_id)
			return


def get_transmission(server_id):
	for transmission in transmissions:
		if transmission.connection_a.server_id == server_id:
			return transmission

		if transmission.connection_b.server_id == server_id:
			return transmission


def get_connection(server_id):
	for transmission in transmissions:
		if transmission.connection_a.server_id == server_id:
			return transmission.connection_a

		if transmission.connection_b.server_id == server_id:
			return transmission.connection_b


def connection_alive(server_id) -> bool:
	for transmission in transmissions:
		if transmission.connection_a.server_id == server_id:
			if transmission.connection_b is not None:
				return True

		if transmission.connection_b is not None:
			if transmission.connection_b.server_id == server_id:
				return True

	return False


def attempting_to_connect(server_id) -> bool:
	for transmission in transmissions:
		if transmission.connection_a.server_id == server_id:
			return True
	return False


def available_initial_connections(block_list) -> bool:
	for transmission in transmissions:

		if transmission.connection_b is None:

			if transmission.connection_a.server_id in block_list:
				continue

			return False

	return True


def check_if_connected(server_id) -> bool:
	for transmission in transmissions:
		if transmission.connection_a.server_id == server_id:
			return True

		if transmission.connection_b is None:
			return False
		elif transmission.connection_b.server_id == server_id:
			return True

	return False
