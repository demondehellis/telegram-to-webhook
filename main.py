import os
import re
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

session_name = "session"
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
webhook_url = os.getenv("WEBHOOK_URL")
chats_str = os.getenv("CHATS")

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start()

    chat_urls = chats_str.split(',')
    chat_ids = [await parse_chat_id(url) for url in chat_urls if url.strip()]
    chat_ids = [chat_id for chat_id in chat_ids if chat_id]

    print(f"Listening to chats: {chat_ids}")

    @client.on(events.NewMessage(chats=chat_ids))
    async def handler(event):
        chat = await event.get_chat()
        sender = await event.get_sender()

        chat_name = await get_chat_name(chat)
        sender_name = await get_sender_name(sender)

        data = {
            "chat_id": event.chat_id,
            "chat_name": chat_name,
            "sender_id": event.sender_id,
            "sender_name": sender_name,
            "message": event.message.message,
        }
        
        try:
            # requests.post(webhook_url, json=data)
            print(f"Webhook sent: {data}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send webhook: {e}")

    async def get_sender_name(sender):
        sender_name = "N/A"
        if hasattr(sender, "username") and sender.username:
            sender_name = f"@{sender.username}"
        elif hasattr(sender, "first_name") and sender.first_name:
            sender_name = sender.first_name
        elif hasattr(sender, "title") and sender.last_name:
            sender_name = sender.title
        return sender_name

    async def get_chat_name(chat) -> str:
        chat_name = 'N/A'
        if hasattr(chat, "username") and chat.username:
            chat_name = f"@{chat.username}"
        elif hasattr(chat, "first_name") and chat.first_name:
            chat_name = chat.first_name
        elif hasattr(chat, "title") and chat.last_name:
            chat_name = chat.title
        return chat_name

    print("Client started. Listening for messages...")
    await client.run_until_disconnected()


async def parse_chat_id(url: str):
    fragment = re.search(r'([^/]+)$', url).group(1)
    fragment = fragment.lstrip('#')

    try:
        if fragment.isdigit() or (fragment.startswith('-') and fragment[1:].isdigit()):
            chat_id = int(fragment)
            entity = await client.get_entity(chat_id)
            return entity.id
        else:
            entity = await client.get_entity(fragment)
            return entity.id
    except Exception as e:
        print(f"Failed to parse chat ID from {url}: {e}")
        return None


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())