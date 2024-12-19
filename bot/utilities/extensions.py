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

loaded_interacts = []
def load_interacts(client: interactions.Client, unload: bool=False, print=print):
	global loaded_interacts
	loaded_interacts = []

	files = [f for f in os.listdir('bot/interacts') if f != '__pycache__']
	interacts = [f.replace('.py', '') for f in files]
	interacts = [None if len(f) < 0 or f.startswith(".") else f for f in interacts]
	
	if not get_config("music.enabled") and 'music' in interacts:
		interacts.remove("music")
  
	if debugging():
		print("Loading interacts" if not unload else "Reloading interacts")
	else:
		print(("Loading interacts" if not unload else "Reloading interacts") + " ... \033[s", flush=True)
	for intr in interacts:
		if not intr:
			continue
		if unload: 
			client.unload_extension(f"interacts.{intr}")
		if debugging():
			print("| " + intr)
		client.load_extension(f"interacts.{intr}")
		loaded_interacts.append(intr)

	if not debugging():
		print(f"\033[udone ({len(loaded_interacts)})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_interacts)})")
