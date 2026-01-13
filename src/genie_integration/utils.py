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

def _create_rich_text_cell(text: str, bold: bool = False) -> dict:
    """Create a rich_text cell for a Slack table."""
    style = {"bold": True} if bold else {}
    element = {"type": "text", "text": str(text)}
    if style:
        element["style"] = style
    return {
        "type": "rich_text",
        "elements": [{
            "type": "rich_text_section",
            "elements": [element]
        }]
    }


def _create_table_block(columns: list, data_array: list) -> dict:
    """Create a Slack table block from columns and data."""
    rows = []
    
    # Header row with bold text
    header_row = [_create_rich_text_cell(col, bold=True) for col in columns]
    rows.append(header_row)
    
    # Data rows
    for row in data_array:
        data_row = [_create_rich_text_cell(cell) for cell in row]
        rows.append(data_row)
    
    return {
        "type": "table",
        "rows": rows
    }


def format_genie_response(genie_message: GenieMessage) -> dict:
    """
    Format a Genie response into Slack blocks.
    
    Returns:
        dict with keys:
            - blocks: list of Slack blocks for the message
            - text: fallback plain text
            - sql_query: SQL query code (if any) for file attachment
    """
    blocks = []
    query_code = None
    text_parts = []

    query = genie_message.attachments[0].query
    text = genie_message.attachments[0].text

    # Add text content as a section block
    text_content = text.content if text else None
    if text_content:
        text_parts.append(text_content)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": text_content}
        })

    if query:
        query_desc = query.description if query else None
        query_code = query.query if query else None

        # Add query description
        if query_desc:
            text_parts.append(query_desc)
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": query_desc}
            })

        # Get query results and create table block
        query_result = genie.get_message_attachment_query_result(
            genie_message.space_id,
            genie_message.conversation_id,
            genie_message.message_id,
            genie_message.attachments[0].attachment_id
        )
        columns = [col.name for col in query_result.statement_response.manifest.schema.columns]
        data_array = query_result.statement_response.result.data_array

        # Create table block
        table_block = _create_table_block(columns, data_array)
        blocks.append(table_block)

    return {
        "blocks": blocks,
        "text": "\n".join(text_parts) if text_parts else "Genie response",
        "sql_query": query_code
    }


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
