import os
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
import ssl
from slack_sdk.web.async_client import AsyncWebClient
import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import GenieMessage
import os
import asyncio
from functools import wraps

w = WorkspaceClient()
genie = w.genie
space_id = os.environ["GENIE_SPACE_ID"]

def get_slack_auth():
    if os.environ.get("IS_LOCAL") == 'true': # For local dev
        token_app = os.environ["TOKEN_APP"]
        token_bot = os.environ["TOKEN_BOT"]
    else:
        token_app = w.dbutils.secrets.get(scope='genie-slack-secret-scope', key='token_app')
        token_bot = w.dbutils.secrets.get(scope='genie-slack-secret-scope', key='token_bot')
    return token_app, token_bot

def start_slack_client():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = AsyncWebClient(token=token_bot, ssl=ssl_context)
    return AsyncApp(client=client, process_before_response=False)

token_app, token_bot = get_slack_auth()
app = start_slack_client()

def extract_text(message):
    query = ""
    for block in message["blocks"]:
        for element in block["elements"]:
            query = "".join([text["text"] if text["type"] else "" for text in element["elements"]])
    return query


def message_poll(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # result_waiter = asyncio.create_task(func(*args, **kwargs))
        result_waiter = func(*args, **kwargs)
        poll_count = 0
        wait = 5

        while poll_count < 20:
            message = genie.get_message(
                result_waiter.space_id,
                result_waiter.conversation_id,
                result_waiter.message_id
            )
            print(message)
            if message.status.value == "COMPLETED":
                return result_waiter.result()

            elif message.status.value == "FAILED":
                raise LookupError("Genie failed to return a response")

            poll_count += 1
            await asyncio.sleep(wait)
        raise TimeoutError("Genie did not return a response")
    return wrapper

@message_poll
def async_genie_start_conv(*args, **kwargs):
    return genie.start_conversation(*args, **kwargs)

@message_poll
def async_genie_create_message(*args, **kwargs):
    return genie.create_message(*args, **kwargs)

def format_genie_response(genie_message: GenieMessage) -> str:
    query_desc = query_code = table_text = None

    query = genie_message.attachments[0].query
    text = genie_message.attachments[0].text

    text_content = text.content if text else None
    if query:
        query_desc = query.description if query else None
        query_code = query.query if query else None


        query_result = genie.get_message_attachment_query_result(
            genie_message.space_id,
            genie_message.conversation_id,
            genie_message.message_id,
            genie_message.attachments[0].attachment_id
        )
        columns = [col.name for col in query_result.statement_response.manifest.schema.columns]
        data_array = query_result.statement_response.result.data_array
        # Determine maximum width for each column (consider header and row values)
        widths = [len(col) for col in columns]
        for row in data_array:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        # Create the header row
        header = " | ".join(col.ljust(widths[i]) for i, col in enumerate(columns))
        # Create a separator row
        separator = "-|-".join("-" * widths[i] for i in range(len(columns)))

        # Build the rows of the table
        rows = [header, separator]
        for row in data_array:
            row_str = " | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))
            rows.append(row_str)

        # Wrap the table in triple backticks to format as a code block

        table_text =  "```\n" + "\n".join(rows) + "\n```"
    text_result = "\n".join([s for s in [text_content, query_desc, table_text, query_code] if s])
    return text_result

async def send_thinking_message(say) -> str:
    response = await say(text="Genie is thinking...")
    return response.get("ts")

async def delete_message(channel: str, ts: str) -> None:
    try:
        await app.client.chat_delete(channel=channel, ts=ts)
    except Exception as e:
        print(f"Error deleting message: {e}")

conv_tracker = {}

@app.event("assistant_thread_started")
async def publish_home_view(event, say, client, logger):
    thread_ts = event["assistant_thread"]["thread_ts"]

    await say(
        text="Select a Genie room",  # Required fallback
        thread_ts=thread_ts,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Select Genie Room"
                },
                "accessory": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Genie room name",
                        "emoji": True
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "*plain_text option 0*",
                                "emoji": True
                            },
                            "value": "value-0"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "*plain_text option 1*",
                                "emoji": True
                            },
                            "value": "value-1"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "*plain_text option 2*",
                                "emoji": True
                            },
                            "value": "value-2"
                        }
                    ],
                    "action_id": "static_select-action"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": " "
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Confirm",
                        "emoji": True
                    },
                    "value": "click_me_123",
                    "action_id": "button-action"
                }
            }
        ]
    )

# Listens to incoming messages
@app.event("message")
async def message_hello(message, say, client):
    print("Received: ", message, type(message))
    thinking_ts = await send_thinking_message(say)
    thread_ts = message.get("thread_ts")
    conv_id = conv_tracker.get(thread_ts)
    query = extract_text(message)
    try:
        if not conv_id:
            genie_message = await async_genie_start_conv(space_id, query)
            # genie_message = genie.start_conversation(space_id, query)

            conv_tracker[thread_ts] = genie_message.conversation_id
        else:
            genie_message = await async_genie_create_message(space_id, conv_id, query)

        text = format_genie_response(genie_message)
        print("Query output:", genie_message)

    except TimeoutError as e:
        text=str(e)
    except LookupError as e:
        text=str(e)
    await delete_message(message.get("channel"), thinking_ts)
    await say(text=text, thread_ts=message.get("thread_ts"))


# Start the app
async def main():
    handler = AsyncSocketModeHandler(app, token_app)
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())


