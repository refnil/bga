#!/usr/bin/env python3
"""Bot to create games on discord."""
from collections import ChainMap, defaultdict
import typing
import json
from dataclasses import dataclass, field
import logging.handlers
import argparse

from .bga_account import BGAAccount
from .bga_game_list import bga_game_message_list, get_game_list, is_game_valid
from .bga_create_game import create_bga_game, setup_bga_game
from .utils import send_help

LOG_FILENAME = "errs"
logger = logging.getLogger(__name__)
logging.getLogger("discord").setLevel(logging.WARN)
# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=10000000, backupCount=0)
formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(prog="bga-utils")
parser.add_argument('--users-path', required=True)
parser.add_argument('--operations-path', required=True)
parser.add_argument("--validate", default=False, action='store_true')
parser.add_argument("--dry-run", default=False, action='store_true')


@dataclass
class User:
    name: str
    password: typing.Optional[str] = None

    @property
    def has_password(self):
        return self.password is not None


@dataclass
class Operation:
    game: str
    toCreate: str
    toInvite: typing.Set[str] = field(default_factory=set)
    options: typing.Dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    users_path: str
    operations_path: str
    validate: bool
    dry_run: bool

    def users_gen(self):
        with open(self.users_path) as f:
            users = json.load(f)
            if isinstance(users, list):
                for user in users:
                    if isinstance(user, str):
                        yield User(user)
                    else:
                        yield User(user['username'], user['password'])

    def users(self):
        return {user.name: user for user in self.users_gen()}

    def operations(self):
        errors = []

        def parse_list(elems, context):
            for elem in elems:
                yield from parse_any(elem, context)

        def parse_dict(elem, parent_context: ChainMap):
            context = parent_context.new_child()

            toCreate = elem.get("toCreate")
            if toCreate is not None:
                context["toCreate"] = toCreate

            toInvite = elem.get("toInvite")
            if toInvite is not None:
                if isinstance(toInvite, str):
                    context["toInvite"] = context.get("toInvite", []) + [toInvite]
                elif isinstance(toInvite, list):
                    context["toInvite"] = context.get("toInvite", []) + toInvite
                else:
                    errors.append(Exception("toInvite", toInvite))

            options = elem.get("options")
            if options is not None:
                context["options"] = context.get("options", {}) | options

            game = elem.get("game")
            if game is not None:
                yield Operation(game, **context)

            yield from parse_any(elem.get("children"), context)

        def parse_any(elem, context: ChainMap):
            if elem is None:
                pass
            elif isinstance(elem, dict):
                yield from parse_dict(elem, context)
            elif isinstance(elem, list):
                yield from parse_list(elem, context)
            else:
                errors.append(Exception(elem))

        with open(self.operations_path) as f:
            ops = list(parse_any(json.load(f), ChainMap()))
            return (ops, errors)


def apply_operations(creater: User, operations: typing.List[Operation], dry_run):
    account = BGAAccount()
    if not creater.has_password:
        raise Exception("no password here...")

    account.login(creater.name, creater.password)

    player_id = account.get_player_id(creater.name)

    tables = account.get_tables(player_id) or {}
    games = get_game_list()[0]

    for op in operations:
        found_table = None

        game_id = games[op.game]
        op_names = set(op.toInvite) | {op.toCreate}

        for table in tables.values():
            if game_id != int(table['game_id']):
                continue
            if player_id != table["table_creator"]:
                continue

            player_names = {player["fullname"] for player in table["players"].values()}
            if player_names != op_names:
                continue

            found_table = table
            break

        if found_table is not None:
            logger.debug(f"Found table {op=}")
            break

        if dry_run:
            logger.info(f"Dry run: ${op=}")
        else:
            create_bga_game(account, op.game, op.toInvite, op.options)

    account.logout()
    account.close_connection()


def main():
    config = Config(**vars(parser.parse_args()))

    users = config.users()
    (operations, errors) = config.operations()
    op_per_creater = defaultdict(list)

    (game_list, _nothing) = get_game_list()

    for op in operations:
        creater = op.toCreate

        if creater in op.toInvite:
            errors.append(Exception("Cannot invite to own game", op))

        asUser = users.get(creater)
        if asUser is None or not asUser.has_password:
            errors.append(Exception("Missing password to create game", op))

        if game_list.get(op.game) is None:
            errors.append(Exception("Cannot find game", op))

        op_per_creater[creater].append(op)

    if len(errors) > 0:
        print(errors)
        return

    if config.validate:
        print("config validated")
        print(operations)
        return

    print(users, operations, errors)

    for username, ops in op_per_creater.items():
        user = users[username]
        apply_operations(user, ops, config.dry_run)


if __name__ == "__main__":
    main()
