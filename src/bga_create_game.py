import logging.handlers
import re
from bga_account import BGAAccount

from utils import normalize_name

logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.WARN)


async def setup_bga_game(message, p1_discord_id, game, players, options):
    """Setup a game on BGA based on the message.
    Return a text error or ""
    """
    account, errs = await get_active_session(p1_discord_id)
    if errs:
        return errs
    # Use user prefs set in !setup if set
    logins = get_all_logins()
    if (
        str(message.author.id) in logins
        and ("username" in logins[str(message.author.id)] and len(logins[str(message.author.id)]["username"]) > 0)
        and ("password" in logins[str(message.author.id)] and len(logins[str(message.author.id)]["username"]) > 0)
    ):
        user_data = logins[str(message.author.id)]
    else:
        return "Need BGA credentials to setup game. Run !setup."
    user_prefs = {}
    all_game_prefs = {}
    # bga options and bga game options aren't necessarily defined
    if "bga options" in user_data:
        user_prefs = user_data["bga options"]
    if "bga game options" in user_data:
        all_game_prefs = user_data["bga game options"]
    if "players" not in options:  # play with exactly as many players as specified
        author_num = 1
        num_players = len(players) + author_num
        options["players"] = f"{num_players}-{num_players}"
    game_name = normalize_name(game)
    if game_name in all_game_prefs:  # game prefs should override global prefs
        user_prefs.update(all_game_prefs[game_name])
    options.update(user_prefs)
    table_msg = await message.channel.send("Creating table...")
    await create_bga_game(message, account, game, players, p1_discord_id, options)
    await table_msg.delete()
    account.logout()  # Probably not necessary
    account.close_connection()
    return ""


def create_bga_game(bga_account: BGAAccount, game, players, options):
    """Create the actual BGA game."""
    # If the player is a discord tag, this will be
    # {"bga player": "discord tag"}, otherwise {"bga player":""}
    error_players = []
    table_id, create_err = bga_account.create_table(game)
    if len(create_err) > 0:
        logger.info(f"Cannot create game ${game=}")
        return
    valid_bga_players = []
    err_msg = bga_account.set_table_options(options, table_id)
    if err_msg:
        logger.info(f"Cannot set table options ${game=} ${options=}")
        return
    for bga_player in players:
        bga_player_id = bga_account.get_player_id(bga_player)
        if bga_player_id == -1:
            error_players.append(f"`{bga_player}` is not a BGA player")
        else:
            error = bga_account.invite_player(table_id, bga_player_id)
            if len(error) > 0:  # If there's error text
                error_players.append(f"Unable to add `{bga_player}` because {error}")
            else:
                valid_bga_players.append(bga_player)
    bga_account.open_table(table_id)
    return table_id
