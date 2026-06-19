import os
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

requests.post(
    WEBHOOK_URL,
    json={
        "content": "🚨 Test message!"
    }
)