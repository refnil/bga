import logging.handlers

from .bga_account import BGAAccount


logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.WARN)


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
