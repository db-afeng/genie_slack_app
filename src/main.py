import asyncio
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from slack_app.app_setup import app, token_app
import slack_app.handlers

async def main():
    handler = AsyncSocketModeHandler(app, token_app)
    await handler.start_async()

if __name__ == "__main__":
    asyncio.run(main())
