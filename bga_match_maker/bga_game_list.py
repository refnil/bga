"""Get/cache available games. Cache is bga_game_list.json."""
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import time

import requests

from .utils import normalize_name

logging.getLogger("aiohttp").setLevel(logging.WARN)

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


GAME_LIST_PATH = "bga_game_list.json"


def get_game_list_from_cache():
    with open(GAME_LIST_PATH, "r") as f:
        logger.debug("Loading game list from cache because the game list has been checked in the last week.")
        return json.loads(f.read()), ""


def get_game_list():
    """Get the list of games and numbers BGA assigns to each game.
    The url below should be accessible unauthenticated (test with curl).
    """
    sixhours = 21600
    if False and os.path.exists(GAME_LIST_PATH) and time.time() - sixhours < os.path.getmtime(GAME_LIST_PATH):
        return get_game_list_from_cache()
    url = "https://boardgamearena.com/gamelist?section=all"
    with requests.Session() as session:
        with session.get(url) as response:
            if response.status_code >= 400:
                # If there's a problem with getting the most accurate list, use cached version
                with open(GAME_LIST_PATH, "r") as f:
                    logger.debug("Loading game list from cache because BGA was unavailable")
                    return json.loads(f.read()), ""
            html = response.text

            lines = html.splitlines()

            # Search a line defining the variable globalUserInfos=
            infosLine = next(line for line in lines if "globalUserInfos=" in line)

            # Load the json object
            # Start at first { and remove the last char (a ';')
            infos = json.loads(infosLine[infosLine.index("{"):-1])

            game_list = infos["game_list"]

            games = {}

            for game in game_list:
                name = game["display_name_en"]
                id = game["id"]
                codename = game["name"]

                games[name] = {
                    "id": id,
                    "codename": codename
                }

            # We need to read AND update the existing json because the BGA game list doesn't
            # include "games in review" that may be saved in the json.
            update_games_cache(games)
            return games, ""


def update_games_cache(games):
    with open(GAME_LIST_PATH, "w") as f:
        f.write(json.dumps(games, indent=2) + "\n")


def is_game_valid(game):
    # Check if any words are games
    games, errs = get_game_list()
    if errs:
        games, errs = get_game_list_from_cache()
    normalized_games = [normalize_name(g) for g in games]
    normalized_game = normalize_name(game)
    return normalized_game in normalized_games
