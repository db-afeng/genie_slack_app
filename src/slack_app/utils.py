from slack_app.app_setup import app


def extract_text(message):
    query = ""
    for block in message["blocks"]:
        for element in block["elements"]:
            # Corrected list comprehension to handle elements with 'type' attribute (like 'text')
            query = "".join(
                [
                    text.get("text", "")
                    for text in element["elements"]
                    if text.get("type") == "text"
                ]
            )
    return query


async def send_thinking_message(say) -> str:
    response = await say(text="Genie is thinking...")
    return response.get("ts")


async def delete_message(channel: str, ts: str) -> None:
    try:
        await app.client.chat_delete(channel=channel, ts=ts)
    except Exception as e:
        print(f"Error deleting message: {e}")
