import os
import interactions
from utilities.config import debugging, get_config, on_prod
loaded_extensions = []

def load_extensions(client: interactions.Client, unload: bool=False, print=print):
	global loaded_extensions
	loaded_extensions = []

	files = [f for f in os.listdir('bot/extensions') if f != '__pycache__']
	extensions = [f.replace('.py', '') for f in files]
	extensions = [None if len(f) < 0 else f for f in extensions]
	
	if not get_config("music.enabled") and 'music' in extensions:
		extensions.remove("music")

	if not on_prod and "welcome_messages" in extensions:
		extensions.remove("welcome_messages")
  
	if debugging():
		print("Loading extensions" if not unload else "Reloading extensions")
	else:
		print(("Loading extensions" if not unload else "Reloading extensions") + " ... \033[s", flush=True)
	for ext in extensions:
		if not ext:
			continue
		if unload: 
			client.unload_extension(f"extensions.{ext}")
		if debugging():
			print("| " + ext)
		client.load_extension(f"extensions.{ext}")
		loaded_extensions.append(ext)

	if not debugging():
		print(f"\033[udone ({len(loaded_extensions)})", flush=True)
		print("\033[999B", end="", flush=True)
	else:
		print(f"Done ({len(loaded_extensions)})")
