import os


def get_slack_auth():
    token_app = os.environ["TOKEN_APP"]
    token_bot = os.environ["TOKEN_BOT"]
    return token_app, token_bot
