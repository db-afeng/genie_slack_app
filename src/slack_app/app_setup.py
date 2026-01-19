import ssl
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from config.slack_auth import get_slack_auth


def start_slack_client(token_bot):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = AsyncWebClient(token=token_bot, ssl=ssl_context)
    return AsyncApp(client=client, process_before_response=False)


token_app, token_bot = get_slack_auth()
app = start_slack_client(token_bot)
