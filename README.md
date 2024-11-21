<div align="center">
    <img src="https://avatars.githubusercontent.com/u/160534184?s=280&v=4" width="128" height="128">
</div>

# <div align="center"> The World Machine </div>

<div align="center">

### A discord bot based off the videogame OneShot, and built using the `interactions-py` library.

For more information on what you can do with this bot, check out our [website](https://www.theworldmachine.xyz/invite).
</div>

---
## Contributing:

### Localization
In `bot/data/locales` there are YAML files with the localization strings. Using `en.yml` as a base, you are free to contribute your own language to the bot.
> [!NOTE] 
> `/music`, `/wool` & `/transmission` do not have localizations yet
### Pull Requests
As with any other repo, pull requests and bug reporting is always welcomed.

### Crediting
Contributing in any way to the discord bot will have your name be put in the website's credits and a role assigned on the discord.

---
## Running your own instance:
### Step 0: Install Python 3.11
For Windows/macOS you can get the installer [here](https://www.python.org/downloads/release/python-31110/), for Linux you can search for your package manager's solution.<br>

You can check which version of python you're running with this command
```commandline
C:\> python --version
Python 3.11.10
```

### Step 0.1: Install pipenv
```commandline
C:\> python -m pip install pipenv
```

### Step 1: Install Dependencies.
(after cloning the repo, and navigating to that folder)
To install all of the dependencies, run this in your console:
```commandline
D:\...\the-world-machine> pipenv install
```
This should install all dependencies needed to run the bot.

### Step 2: Fill in configs
There is file called `bot-config.example.yml` which has stuff to configure the bot, including the bot token, database endpoints and api keys. Rename or duplicate this file to `bot-config.yml` in the same folder and fill it in. <br>
A similar file is also located in the lavalink directory.

### Step 3: Running the bot.
```commandline
pipenv run bot
```
