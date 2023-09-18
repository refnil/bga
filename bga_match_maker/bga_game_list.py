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


GAME_LIST_PATH = "src/bga_game_list.json"


def get_game_list_from_cache():
    with open(GAME_LIST_PATH, "r") as f:
        logger.debug("Loading game list from cache because the game list has been checked in the last week.")
        return json.loads(f.read()), ""


def get_game_list():
    """Get the list of games and numbers BGA assigns to each game.
    The url below should be accessible unauthenticated (test with curl).
    """
    sixhours = 21600
    if time.time() - sixhours < os.path.getmtime(GAME_LIST_PATH):
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
            # Parse an HTML list
            results = re.findall(r"item_tag_\d+_(\d+)[\s\S]*?name\">\s+([^<>]*)\n", html)
            # Sorting games so when writing, git picks up on new entries
            results.sort(key=lambda x: x[1])
            games = {}
            for r in results:
                games[r[1]] = int(r[0])
            # We need to read AND update the existing json because the BGA game list doesn't
            # include "games in review" that may be saved in the json.
            update_games_cache(games)
            return games, ""


def bga_game_message_list():
    """List the games that BGA currently offers as a list of str messages less than 1000 chars."""
    game_data, err_msg = get_game_list()
    if len(err_msg) > 0:
        return err_msg
    game_list = list(game_data.keys())
    tr_games = [g[:22] for g in game_list]
    retlist = []
    retmsg = ""
    for i in range(len(tr_games) // 5 + 1):
        retmsg += "\n"
        for game_name in tr_games[5 * i : 5 * (i + 1)]:
            retmsg += "{:<24}".format(game_name)
        if i % 15 == 0 and i > 0 or i == len(tr_games) // 5:
            # Need to truncate at 1000 chars because max message length for discord is 2000
            retlist.append("```" + retmsg + "```")
            retmsg = ""
    return retlist


def update_games_cache(games):
    with open(GAME_LIST_PATH, "r") as f:
        file_text = f.read()
        file_games = json.loads(file_text)
        games.update(file_games)
    with open(GAME_LIST_PATH, "w") as f:
        f.write(json.dumps(games, indent=2) + "\n")


async def is_game_valid(game):
    # Check if any words are games
    games, errs = get_game_list()
    if errs:
        games, errs = get_game_list_from_cache()
    normalized_games = [normalize_name(g) for g in games]
    normalized_game = normalize_name(game)
    return normalized_game in normalized_games
