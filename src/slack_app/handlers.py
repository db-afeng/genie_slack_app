import asyncio
import os
from slack_bolt.async_app import AsyncApp

# Import from other modules
from genie_integration.client import genie, space_id
from genie_integration.utils import message_poll, async_genie_start_conv, async_genie_create_message, format_genie_response
from slack_app.utils import send_thinking_message, extract_text, delete_message
from slack_app.app_setup import app

# Global conversation tracker (can be managed differently, e.g., via a database)
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