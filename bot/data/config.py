import yaml

with open('bot-config.yml', 'r') as f:
    data = yaml.safe_load(f)
    print("Loaded configuration")

def get_config(path: str, data=data, ignore_None: bool = False) -> any:

    for key in path.split('.'):
        if key in data:
            data = data[key]
        else:
            if ignore_None:
                return None;
            raise KeyError(f"Key '{key}' not found in the configuration.")

    return data