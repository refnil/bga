#!/usr/bin/env python3
"""Bot to create games on discord."""
from collections import ChainMap
import typing
import json
from dataclasses import dataclass, field
import logging.handlers
import argparse

from bga_game_list import bga_game_message_list, is_game_valid
from bga_create_game import setup_bga_game
from utils import send_help

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
        return list(self.users_gen())

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


config = Config(**vars(parser.parse_args()))

users = config.users()
(operations, errors) = config.operations()
print(users, operations, errors)
