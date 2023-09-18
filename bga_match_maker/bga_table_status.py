"""Functions to check the status of an existing game on BGA."""
import datetime
import logging
from logging.handlers import RotatingFileHandler

from utils import normalize_name

logging.getLogger("discord").setLevel(logging.WARN)

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def get_bga_alias(game_name):
    # BGA uses different names *in game* than for game creation, so recognize this.
    aliases = {
        "redsevengame": "red7",
        "sechsnimmt": "6nimmt",
        "sevenwonders": "7wonders",
        "sevenwondersduel": "7wondersduel",
        "yatzy": "yahtzee",  # `yatzy` is due to it initially using the French name due to copyright concerns
        "arnak": "lostruinsofarnak",
    }
    if normalize_name(game_name) in aliases:
        return aliases[normalize_name(game_name)]
    return normalize_name(game_name)


async def send_active_tables_list(message, bga_account, table, game_name):
    # If a game has not started, but it is scheduled, it will be None here.
    if table["gamestart"]:
        gamestart = table["gamestart"]
    else:
        gamestart = table["scheduled"]
    days_age = (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(int(gamestart))).days
    percent_done, num_moves, table_url = bga_account.get_table_metadata(table)
    percent_text = ""
    if percent_done:  # If it's at 0%, we won't get a number
        percent_text = f"\t\tat {percent_done}%"
    p_names = []
    for p_id in table["players"]:
        p_name = table["players"][p_id]["fullname"]
        # Would include this, but current_player_nbr seems to be the opposite value of expected for a player
        # if table["players"][p_id]["table_order"] == str(table["current_player_nbr"]):
        #    p_name = '**' + p_name + ' to play**'
        p_names.append(p_name)
    msg_to_send = f"__{game_name}__\t\t[{', '.join(p_names)}]\t\t{days_age} days old {percent_text}\t\t{num_moves} moves\n\t\t<{table_url}>\n"
    logger.debug("Sending:" + msg_to_send)
    await message.channel.send(msg_to_send)
