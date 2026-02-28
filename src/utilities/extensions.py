import os

import interactions

from utilities.config import debugging, get_config


def assign_events(client: interactions.Client):
	files = [f for f in os.listdir("src/extensions/events") if f != "__pycache__"]
	events = [f.replace(".py", "") for f in files]
	events = [None if len(f) < 0 or f.startswith(".") else f for f in events]
	if not get_config("modules.welcome", typecheck=bool) and "MemberAdd" in events:
		print("Welcome Messages are disabled")
		events.remove("MemberAdd")
	if not get_config("modules.devcommands", typecheck=bool) and "MessageCreate" in events:
		print("Developer Commands are disabled [bot]")
		events.remove("MessageCreate")

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

	files = [f for f in os.listdir("src/extensions/commands") if f != "__pycache__"]
	commands = [f.replace(".py", "") for f in files]
	commands = [None if len(f) < 0 or f.startswith(".") else f for f in commands]
	commands.append("interactions.ext.jurigged")
	if not get_config("modules.music", typecheck=bool) and "music" in commands:
		print("Music commands are disabled")
		commands.remove("music")

	if debugging():
		print("Loading commands" if not unload else "Reloading commands")
	else:
		print(
			("Loading commands" if not unload else "Reloading commands") + " ... \033[s",
			flush=True,
		)
	for cmd in commands:
		if not cmd:
			continue
		if unload:
			client.unload_extension(
				f"extensions.commands.{cmd}" if not cmd == "interactions.ext.jurigged" else "interactions.ext.jurigged"
			)
		if debugging():
			print("| " + cmd)
		client.load_extension(
			f"extensions.commands.{cmd}" if not cmd == "interactions.ext.jurigged" else "interactions.ext.jurigged"
		)
		loaded_commands.append(cmd)

	if not debugging():
		print(f"\033[udone ({len(loaded_commands)})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_commands)})")
