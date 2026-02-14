import os
from typing import Any

import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

session_name = "session"
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
webhook_url = os.getenv("WEBHOOK_URL")


def get_excluded_chat_ids():
    excluded_chats = os.getenv("EXCLUDED_CHATS")
    if excluded_chats:
        return [chat.strip() for chat in excluded_chats.split(",")]
    return []


def get_allowed_chat_ids():
    allowed_chats = os.getenv("ALLOWED_CHATS")
    if allowed_chats:
        return [chat.strip() for chat in allowed_chats.split(",")]
    return []


client = TelegramClient(session_name, api_id, api_hash)


# New helper: build headers for webhook requests
def get_webhook_headers() -> dict[str, str]:
    """Return headers for webhook requests.

    Reads CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET from the environment
    and, if present, includes them as Cloudflare Access headers. Always
    sets Content-Type: application/json.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}

    cf_id = os.getenv("CF_ACCESS_CLIENT_ID")
    cf_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")

    if cf_id:
        headers["CF-Access-Client-Id"] = cf_id
    if cf_secret:
        headers["CF-Access-Client-Secret"] = cf_secret

    return headers


async def main():
    # Ensure webhook URL exists before starting the client
    if not webhook_url:
        print("WEBHOOK_URL is not set. Set the WEBHOOK_URL environment variable to a valid endpoint and restart.")
        return

    # Log presence of Cloudflare Access headers (but do not print secrets)
    headers = get_webhook_headers()
    if "CF-Access-Client-Id" in headers:
        print("CF-Access-Client-Id header will be sent with webhooks.")
    if "CF-Access-Client-Secret" in headers:
        print("CF-Access-Client-Secret header will be sent with webhooks.")

    await client.start()
    excluded_chat_ids = get_excluded_chat_ids()
    allowed_chat_ids = get_allowed_chat_ids()

    @client.on(events.NewMessage())
    async def handler(event):
        if str(event.chat_id) in excluded_chat_ids:
            print(f"Excluded chat ID {event.chat_id}, skipping webhook.")
            return
        if allowed_chat_ids and str(event.chat_id) not in allowed_chat_ids:
            print(f"Chat ID {event.chat_id} not in allowed list, skipping webhook.")
            return

        data = await build_webhook_data(event)
        try:
            headers = get_webhook_headers()
            # include headers when sending the webhook
            resp = requests.post(webhook_url, json=data, headers=headers, timeout=10)
            resp.raise_for_status()
            print(f"Webhook sent (status={resp.status_code}): {data}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send webhook: {e}")

    async def build_webhook_data(event) -> dict[str, str | Any]:
        chat = await event.get_chat()
        sender = await event.get_sender()

        print(chat)
        print(sender)

        chat_name = await get_chat_name(chat)
        chat_type = await get_chat_type(event, chat)
        sender_name = await get_sender_name(sender)

        return {
            "chat_id": event.chat_id,
            "chat_name": chat_name,
            "chat_type": chat_type,
            "sender_id": event.sender_id,
            "sender_name": sender_name,
            "message": event.message.message,
        }

    async def get_sender_name(sender):
        sender_name = "N/A"
        if hasattr(sender, "username") and sender.username:
            sender_name = f"@{sender.username}"
        elif hasattr(sender, "first_name") and sender.first_name:
            sender_name = sender.first_name
        elif hasattr(sender, "title") and sender.title:
            sender_name = sender.title
        return sender_name

    async def get_chat_name(chat) -> str:
        chat_name = 'N/A'
        if hasattr(chat, "username") and chat.username:
            chat_name = f"@{chat.username}"
        elif hasattr(chat, "first_name") and chat.first_name:
            chat_name = chat.first_name
        elif hasattr(chat, "title") and chat.title:
            chat_name = chat.title
        return chat_name

    async def get_chat_type(event, chat) -> str:
        if event.is_private:
            return "direct"

        if getattr(chat, "broadcast", False):
            return "channel"

        if getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False):
            return "group"

        if event.is_group:
            return "group"
        if event.is_channel:
            return "channel"

        return "unknown"

    print("Client started. Listening for messages...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
