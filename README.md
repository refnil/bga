# BGA match maker

To run:
```bash
>  poetry run bga-match-maker --users-path users.json --operations-path games.json
```

`users.json` looks like:
```json
{
    "users": [
        {
            "username": "account 1",
            "password": "the password of account 1"
        },
        "account 2",
        "account 3"
    ]
}
```

`operations.json` looks like:
```json
{
    "toCreate": "account 1",
    "options": {
        "speed": "1/2days"
    },
    "limit": 1,
    "children": [
        {
            "toInvite": "account 2",
            "game": "Yahtzee",
            "options": {
                "restrictgroup": "My friends",
                "players": 2
            }
        }
    ]
}
```

## License

Apache2
