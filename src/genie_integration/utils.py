import asyncio
from functools import wraps
from databricks.sdk.service.dashboards import GenieMessage
from genie_integration.client import genie # Import genie client

def message_poll(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
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


def format_genie_selection():
    """
    Generates a Slack block for selecting a Genie Room, by fetching all
    genie spaces using a Databricks Python SDK call and then
    creating options with room names as text and room IDs as values.

    Returns:
        list: A list of dictionaries representing the Slack block.
    """

    genie_rooms = genie.list_spaces() # Fetch genie rooms using the placeholder

    options = []
    # Iterate through the fetched genie room data
    for space in genie_rooms.spaces:
        options.append({
            "text": {
                "type": "plain_text",
                "text": space.title,  # Use genie room name for display text
                "emoji": True
            },
            "value": space.space_id  # Use genie room ID as the value
        })

    # Construct the complete Slack block as a list of dictionaries
    slack_block = [
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
                "options": options,  # Insert the dynamically generated options here
                "action_id": "static_select-action"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": " "  # Empty text for spacing or layout
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Confirm",
                    "emoji": True
                },
                "value": "click_me_123",  # A static value for the button
                "action_id": "button-action"
            }
        }
    ]
    return slack_block
