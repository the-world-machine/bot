import re
from threading import Thread
import time
from termcolor import colored
from yaml import safe_load
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def flatten_emojis(data: dict, parent_key: str=''):
  items = []
  for k, v in data.items():
    key = f"{parent_key}.{k}" if parent_key else k
    if isinstance(v, dict):
      items.extend(flatten_emojis(v, key).items())
    else:
      items.append((key, v))
  return dict(items)
def unflatten_emojis(flat_data: dict) -> dict:
    unflattened = {}
    for flat_key, value in flat_data.items():
        keys = flat_key.split(".")
        d = unflattened
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
    return unflattened
def minify_emoji_names(data):
    if isinstance(data, dict):
        return {key: minify_emoji_names(value) for key, value in data.items()}
    elif isinstance(data, str):
        # replaces all names with "i" for more embed space
        return re.sub(r'(?<=[:])\w+(?=:\d)', 'i', data)
    return data

def load_emojis():
    with open("bot/data/emojis.yml", "r") as f:
        emojis_data = safe_load(f)
        return minify_emoji_names(emojis_data)

emojis = load_emojis()
emoji_subs = []
def on_emojis_update(callback):
    emoji_subs.append(callback)

    def unsubscribe():
        if callback in emoji_subs:
            emoji_subs.remove(callback)
        else:
            raise ValueError(f"Subscription was already removed before.")
    
    return unsubscribe

def update_emoji_dict(emojis_dict, flat_key, emoji_value=None, remove=False):
    keys = flat_key.split('.')
    current_dict = emojis_dict
    for part in keys[:-1]:
        current_dict = current_dict.setdefault(part, {})

    if remove:
        if keys[-1] in current_dict:
            del current_dict[keys[-1]]
    else:
        current_dict[keys[-1]] = emoji_value

class EmojiFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global emojis
        if event.src_path.endswith("emojis.yml"):
            print(f"{colored('┌ Reloading a modified', 'yellow')} ─ emojis.yml")
            old_emojis = emojis
            new_emojis = load_emojis()
            
            old_flat = flatten_emojis(old_emojis)
            new_flat = flatten_emojis(new_emojis)

            removed_emojis = [key for key in old_flat if key not in new_flat]
            added_emojis = [key for key in new_flat if key not in old_flat]
            changed_emojis = [
                key for key in new_flat
                if key in old_flat and new_flat[key] != old_flat[key]
            ]
            
            # └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
            print(colored('│ changes:', 'yellow'), end='')
            if removed_emojis or added_emojis or changed_emojis:
                print()
                if removed_emojis:
                    print(colored('│ ', 'yellow'), end='')
                    for key in removed_emojis:
                        update_emoji_dict(emojis, key, remove=True)
                        print(f"-{key}", end=', ' if key != removed_emojis[-1] else '\n')

                if added_emojis:
                    print(colored('│ ', 'yellow'), end='')
                    for key in added_emojis:
                        update_emoji_dict(emojis, key, emoji_value=new_flat[key])
                        print(f"+{key}", end=', ' if key != added_emojis[-1] else '\n')

                if changed_emojis:
                    print(colored('│ ', 'yellow'), end='')
                    for key in changed_emojis:
                        update_emoji_dict(emojis, key, emoji_value=new_flat[key])
                        print(f"*{key}", end=', ' if key != changed_emojis[-1] else '\n')
            else:
                print(" none...")

            for callback in emoji_subs:
                callback(new_emojis)

            print(colored('└', 'yellow')+" ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─")

def watch_me():
    observer = Observer()
    event_handler = EmojiFileHandler()
    observer.schedule(event_handler, path="bot/data/", recursive=False) # recuuursived
    observer.start()

    try:
        a = False
        from utilities.localization import fnum
        while True:
            time.sleep(60*60*24)
            if a == False:
                print("[ Hello. ]")
                a = 1
            else:
                print(f"[ Hello for the {fnum(a)} time ]")
                a += 1
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

watcher_thread = Thread(target=watch_me)
watcher_thread.daemon = True
watcher_thread.start()