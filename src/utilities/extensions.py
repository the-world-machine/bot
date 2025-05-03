import os
import interactions
from utilities.config import debugging, get_config, on_prod


def assign_events(client: interactions.Client):
	files = [ f for f in os.listdir('bot/extensions/events') if f != '__pycache__']
	events = [f.replace('.py', '') for f in files]
	events = [None if len(f) < 0 or f.startswith(".") else f for f in events]
	if not on_prod and "welcome_messages" in events:
		events.remove("welcome_messages")

	if debugging():
		print("Assigning events")
	else:
		print("Assigning events ... \033[s", flush=True)
	amount = 0
	for event in events:
		if not event:
			continue
		if debugging():
			print("| " + event)
		client.load_extension(f"extensions.events.{event}")
		amount += 1

	if not debugging():
		print(f"\033[udone ({amount})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({amount})")


loaded_commands = []


def load_commands(client: interactions.Client, unload: bool = False, print=print):
	global loaded_commands
	loaded_commands = []

	files = [ f for f in os.listdir('bot/extensions/commands') if f != '__pycache__']
	commands = [f.replace('.py', '') for f in files]
	commands = [None if len(f) < 0 or f.startswith(".") else f for f in commands]

	if not get_config("music.enabled") and 'music' in commands:
		commands.remove("music")

	if debugging():
		print("Loading commands" if not unload else "Reloading commands")
	else:
		print(("Loading commands" if not unload else "Reloading commands") + " ... \033[s", flush=True)
	for cmd in commands:
		if not cmd:
			continue
		if unload:
			client.unload_extension(f"extensions.commands.{cmd}")
		if debugging():
			print("| " + cmd)
		client.load_extension(f"extensions.commands.{cmd}")
		loaded_commands.append(cmd)

	if not debugging():
		print(f"\033[udone ({len(loaded_commands)})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_commands)})")
