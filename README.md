<div align="center">
    <img src="https://avatars.githubusercontent.com/u/160534184?s=280&v=4" width="128" height="128">
</div>

# <div align="center"> The World Machine </div>

<div align="center">

### A discord bot based off the videogame OneShot, and built using the `interactions-py` library.

For more information on what you can do with this bot, check out our [website](https://www.theworldmachine.xyz/invite).

</div>

## [Documentation](./md/en/Documentation.md)

## Contributing

### Localization

In `src/data/locales` there are YAML files with the localization strings. Using `en.yml` as a base, you are free to contribute your own language to the bot. If you need any help with this - you can ask away in the support server which you can find on our [website](https://www.theworldmachine.xyz/invite).

> [!NOTE]
> `/gamble`, `/transmission`, `/sun give`, `/ship` & any slash command names or descriptions - **do not** have localizations yet

### Pull Requests

As with any other repo, pull requests and bug reporting is always welcomed.

### Crediting

Contributing in any way to the discord bot will have your name be put in the website's credits and a role assigned on the discord.

## Running your own instance

### Prerequisites

Make sure you have python 3.13.11 (u can easily install this one via `pyenv`, running next step will ask if u want to install this version if u dont have it) and the `pipenv` module installed.

```commandline
python -m pip install pipenv
```

### Step 1: Install Dependencies

(after cloning the repo, and navigating to that folder)

```commandline
pipenv install
```

### Step 2: Fill in configs

There is file called `bot-config.example.yml` which has stuff to configure the bot, including the bot token, database endpoints and api keys. Rename or duplicate this file to `bot-config.yml` in the same folder and fill it in. <br>
A similar file is also located in the lavalink directory.

### Step 3: Running the bot

```commandline
pipenv run bot
```
