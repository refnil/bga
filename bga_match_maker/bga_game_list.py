"""Get/cache available games. Cache is bga_game_list.json."""
import json
import logging
from logging.handlers import RotatingFileHandler

import requests

from .utils import normalize_name
from .cache_to_file import cache

logger = logging.getLogger(__name__)


@cache("bga_game_list")
def get_game_list():
    """Get the list of games and numbers BGA assigns to each game.
    The url below should be accessible unauthenticated (test with curl).
    """
    url = "https://boardgamearena.com/gamelist?section=all"
    with requests.Session() as session:
        with session.get(url) as response:
            if response.status_code >= 400:
                # If there's a problem with getting the most accurate list, use cached version
                raise Exception("Try to use cache for game list")
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
                    "codename": codename,
                    "full": game
                }

            return games


def is_game_valid(game):
    # Check if any words are games
    games = get_game_list()
    normalized_games = [normalize_name(g) for g in games]
    normalized_game = normalize_name(game)
    return normalized_game in normalized_games
