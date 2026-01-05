import asyncio
import os
from slack_bolt.async_app import AsyncApp

# Import from other modules
from genie_integration.utils import async_genie_start_conv, async_genie_create_message, format_genie_response, format_genie_selection
from slack_app.utils import send_thinking_message, extract_text, delete_message
from slack_app.app_setup import app

# Import database conversation tracker
from database.conv_tracker import (
    init_database, 
    get_conversation, 
    set_conversation, 
    update_conversation_id,
    is_local_mode
)

# Initialize database tables (only in non-local mode)
if not is_local_mode():
    try:
        init_database()
    except Exception as e:
        print(f"Warning: Failed to initialize database: {e}")
        print("The app will continue but database operations may fail.")

@app.event("assistant_thread_started")
async def publish_home_view(event, say, client, logger):
    # Get thread_ts
    thread_ts = event["assistant_thread"]["thread_ts"]

    # retrieve drop down blocks
    blocks = format_genie_selection()

    await say(
        text="Select a Genie room",
        thread_ts=thread_ts,
        blocks=blocks
    )

# Registers the thread's genie space ID
@app.action("static_select-action")
async def register_genie_id(body, ack,):
    await ack()
    thread_ts = body["message"]["thread_ts"]
    selected_genie_room_id = body['actions'][0]['selected_option']['value']
    selected_genie_room_name = body['actions'][0]['selected_option']['text']['text']
    room_details = {
        "genie_room_id": selected_genie_room_id,
        "genie_room_name": selected_genie_room_name
    }
    set_conversation(thread_ts, room_details)

# Delete the home messages
@app.action("button-action")
async def handle_some_action(say, ack, body, logger):
    await ack()
    channel_id = body["channel"]["id"]
    # The 'ts' of the message containing the button (which is the message we want to update)
    message_ts = body["message"]["ts"]
    # The 'thread_ts' of the thread this message belongs to (root of the thread)
    thread_ts = body["message"]["thread_ts"]
    user_id = body["user"]["id"]

    logger.info(f"Confirm button pressed for message {message_ts} in channel {channel_id}, thread {thread_ts}.")

    # Retrieve the stored selection for this specific thread from database/memory
    stored_selection_data = get_conversation(thread_ts) or {}
    selected_room_id = stored_selection_data.get("genie_room_id")
    selected_room_name = stored_selection_data.get("genie_room_name")

    if not selected_room_id or not selected_room_name:
        logger.warning(f"No valid genie room selection found in conv_tracker for thread {thread_ts}. User might have pressed confirm before selecting.")
        await app.client.chat_postEphemeral(
            channel=channel_id,
            thread_ts=thread_ts,
            user=user_id,
            text="Please select a Genie Room from the dropdown before clicking `Confirm`."
        )
        return

    new_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"✅ Genie Room Confirmed: *{selected_room_name}*"
            }
        }
    ]

    response = await app.client.chat_update(
        channel=channel_id,
        ts=message_ts,
        blocks=new_blocks,
        text=f"Genie Room Confirmed: {selected_room_name}" # Fallback text
    )


# Listens to incoming messages
@app.event("message")
async def message_hello(message, say, client):
    print("Received: ", message, type(message))
    thinking_ts = await send_thinking_message(say)
    thread_ts = message.get("thread_ts")
    channel_id = message.get("channel")
    
    # Get conversation details from database/memory
    conv_data = get_conversation(thread_ts)
    if not conv_data:
        await delete_message(channel_id, thinking_ts)
        await say(text="Error: Please select a Genie room first.", thread_ts=thread_ts)
        return
    
    space_id = conv_data.get("genie_room_id")
    conv_id = conv_data.get("conversation_id")
    query = extract_text(message)
    png_bytes = None
    
    try:
        if not conv_id:
            genie_message = await async_genie_start_conv(space_id, query)
            update_conversation_id(thread_ts, genie_message.conversation_id)
        else:
            genie_message = await async_genie_create_message(space_id, conv_id, query)

        text, png_bytes = format_genie_response(genie_message)
        print("Query output:", genie_message)

    except TimeoutError as e:
        text = str(e)
    except LookupError as e:
        text = str(e)
    
    await delete_message(channel_id, thinking_ts)
    
    # Send the text response
    await say(text=text, thread_ts=thread_ts)
    
    # Upload the visualization image if available
    if png_bytes:
        try:
            await client.files_upload_v2(
                channel=channel_id,
                thread_ts=thread_ts,
                file=png_bytes,
                filename="visualization.png",
                title="Query Visualization",
                initial_comment="📊 Visualization of the query results:"
            )
        except Exception as e:
            print(f"Error uploading visualization: {e}")