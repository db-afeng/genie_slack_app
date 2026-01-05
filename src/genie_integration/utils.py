import asyncio
import json
import os
from functools import wraps
from typing import Optional, Tuple
import vl_convert as vlc
from databricks.sdk.service.dashboards import GenieMessage
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
from genie_integration.client import genie, serving  # Import genie client and serving endpoints

# Get the foundation model endpoint from environment variable
FOUNDATION_MODEL_ENDPOINT = os.environ.get("FOUNDATION_MODEL_ENDPOINT", "")

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

def generate_vegalite_spec(columns: list, data_array: list) -> Optional[dict]:
    """
    Calls a Databricks foundation model endpoint to generate a VegaLite spec
    for visualizing the query results.
    
    Args:
        columns: List of column names
        data_array: 2D array of data values
        
    Returns:
        VegaLite spec as a dictionary, or None if generation fails
    """
    if not FOUNDATION_MODEL_ENDPOINT:
        print("Warning: FOUNDATION_MODEL_ENDPOINT not configured, skipping visualization")
        return None
    
    # Prepare the data summary for the prompt
    data_sample = data_array[:10]  # Limit to first 10 rows for prompt
    data_for_prompt = [dict(zip(columns, row)) for row in data_sample]
    
    prompt = f"""You are a data visualization expert. Given the following data, generate a VegaLite specification that best visualizes this data.

Data columns: {columns}
Sample data (first {len(data_sample)} rows): {json.dumps(data_for_prompt, indent=2)}
Total rows: {len(data_array)}

Requirements:
1. Return ONLY a valid VegaLite JSON specification, no other text or explanation
2. The spec should be complete and self-contained with the data embedded
3. Use appropriate chart type based on the data (bar chart for categorical comparisons, line chart for time series, etc.)
4. Include proper axis labels and a title
5. Use a clean, professional color scheme
6. Set width to 600 and height to 400

Embed all {len(data_array)} rows of data in the spec:
{json.dumps([dict(zip(columns, row)) for row in data_array], indent=2)}

Return only the VegaLite JSON spec:"""

    try:
        response = serving.query(
            name=FOUNDATION_MODEL_ENDPOINT,
            messages=[
                ChatMessage(
                    role=ChatMessageRole.USER,
                    content=prompt
                )
            ]
        )
        
        # Extract the response content
        response_text = response.choices[0].message.content
        
        # Try to parse the JSON from the response
        # Handle cases where the model might wrap it in markdown code blocks
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        vegalite_spec = json.loads(response_text)
        return vegalite_spec
        
    except Exception as e:
        print(f"Error generating VegaLite spec: {e}")
        return None


def vegalite_to_png(vegalite_spec: dict) -> Optional[bytes]:
    """
    Converts a VegaLite specification to a PNG image.
    
    Args:
        vegalite_spec: VegaLite specification as a dictionary
        
    Returns:
        PNG image as bytes, or None if conversion fails
    """
    try:
        png_data = vlc.vegalite_to_png(vegalite_spec, scale=2)
        return png_data
    except Exception as e:
        print(f"Error converting VegaLite to PNG: {e}")
        return None


def format_genie_response(genie_message: GenieMessage) -> Tuple[str, Optional[bytes]]:
    """
    Formats the Genie response and optionally generates a visualization.
    
    Args:
        genie_message: The GenieMessage response from the Genie API
        
    Returns:
        Tuple of (text_response, png_bytes or None)
    """
    query_desc = query_code = table_text = None
    png_bytes = None

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
        
        # Generate visualization if we have data
        if data_array and len(data_array) > 0:
            vegalite_spec = generate_vegalite_spec(columns, data_array)
            if vegalite_spec:
                png_bytes = vegalite_to_png(vegalite_spec)
        
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
    return text_result, png_bytes


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
