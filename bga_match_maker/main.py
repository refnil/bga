from collections import ChainMap, defaultdict
import typing
import json
from dataclasses import dataclass, field
import logging.handlers
import argparse

from .bga_account import BGAAccount
from .bga_game_list import get_game_list
from .bga_create_game import create_bga_game

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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
            loaded = json.load(f)
            users = None

            if isinstance(loaded, list):
                users = loaded
            elif isinstance(loaded, dict):
                users = loaded.get("users")

            if users is None:
                raise Exception("users.json has wrong format")

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

        def make_operation(game, context):
            return Operation(game, **context)

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
                yield make_operation(game, context)

            yield from parse_any(elem.get("children"), context)
            yield from parse_any(elem.get("c"), context)

        def parse_any(elem, context: ChainMap):
            if elem is None:
                pass
            elif isinstance(elem, dict):
                yield from parse_dict(elem, context)
            elif isinstance(elem, list):
                yield from parse_list(elem, context)
            elif isinstance(elem, str):
                yield make_operation(elem, context)
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
    games = get_game_list()

    for op in operations:
        try:
            found_table = None

            game_id = games[op.game]["id"]
            op_names = set(op.toInvite) | {op.toCreate}

            for table in tables.values():
                # The table has the right game
                if game_id != int(table['game_id']):
                    continue

                # The right person created the table
                if player_id != table["table_creator"]:
                    continue

                player_names = {player["fullname"] for player in table["players"].values()}
                # If players are missing from the expected name list, then abort
                if player_names < op_names:
                    continue

                # Check that parameters for the game are correct
                if len(op.options) > 0:
                    # Check the player count if available
                    players = op.options.get("players", None)
                    if players is not None:
                        if str(players) != table["max_player"]:
                            continue

                    # Check options that are handle by changeoption.html
                    # Remove options that are set via other paths than changeoption.html
                    options_copy = dict(op.options)
                    options_copy.pop("mode", None)
                    options_copy.pop("minrep", None)
                    options_copy.pop("presentation", None)
                    options_copy.pop("levels", None)
                    options_copy.pop("players", None)
                    options_copy.pop("restrictgroup", None)
                    options_copy.pop("lang", None)

                    optionsToCheck = account.parse_options(options_copy, table["id"], games[op.game]["codename"])

                    allOptionOK = False
                    for optionToCheck in optionsToCheck:
                        if optionToCheck["path"] != "/table/table/changeoption.html":
                            # Only handle changeoption for now
                            continue
                        optionIdToCheck = optionToCheck["params"]["id"]
                        optionValueToCheck = optionToCheck["params"]["value"]
                        if table["options"].get(str(optionIdToCheck)) != str(optionValueToCheck):
                            break
                    else:
                        allOptionOK = True

                    if not allOptionOK:
                        continue

                found_table = table
                break

            if found_table is not None:
                logger.info(f"Found table. Skipping creation. {op=}")
                continue

            if dry_run:
                logger.info(f"Create game (DRY RUN): ${op=}")
            else:
                logger.info(f"Creating game. ${op=}")
                create_bga_game(account, op.game, op.toInvite, op.options)
        except Exception as e:
            logger.exception(e)

    account.logout()
    account.close_connection()


def main():
    config = Config(**vars(parser.parse_args()))

    users = config.users()
    (operations, errors) = config.operations()
    op_per_creater = defaultdict(list)

    game_list = get_game_list()

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

    for username, ops in op_per_creater.items():
        user = users[username]
        apply_operations(user, ops, config.dry_run)


if __name__ == "__main__":
    # BGAAccount().get_game_info("wingspan")
    main()
