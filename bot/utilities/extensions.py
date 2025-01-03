import os
import interactions
from utilities.config import debugging, get_config, on_prod


def assign_events(client: interactions.Client):
	files = [f for f in os.listdir('bot/events') if f != '__pycache__']
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
		client.load_extension(f"events.{event}")
		amount += 1

	if not debugging():
		print(f"\033[udone ({amount})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({amount})")


loaded_modules = []


def load_modules(client: interactions.Client,
                 unload: bool = False,
                 print=print):
	global loaded_modules
	loaded_modules = []

	files = [f for f in os.listdir('bot/modules') if f != '__pycache__']
	modules = [f.replace('.py', '') for f in files]
	modules = [None if len(f) < 0 or f.startswith(".") else f for f in modules]

	if not get_config("music.enabled") and 'music' in modules:
		modules.remove("music")

	if debugging():
		print("Loading modules" if not unload else "Reloading modules")
	else:
		print(("Loading modules" if not unload else "Reloading modules") +
		      " ... \033[s",
		      flush=True)
	for intr in modules:
		if not intr:
			continue
		if unload:
			client.unload_extension(f"modules.{intr}")
		if debugging():
			print("| " + intr)
		client.load_extension(f"modules.{intr}")
		loaded_modules.append(intr)

	if not debugging():
		print(f"\033[udone ({len(loaded_modules)})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_modules)})")
