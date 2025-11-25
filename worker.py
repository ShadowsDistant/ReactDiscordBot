"""
Cloudflare Workers entry point for Discord bot using Interactions API.
This allows the bot to run on Cloudflare Workers as a webhook-based application.
"""

import json
import os
from typing import Any, Dict, Optional

from discord_interactions import (
    InteractionType,
    InteractionResponseType,
    verify_key,
)


class DiscordInteractionHandler:
    """Handles Discord interactions for Cloudflare Workers deployment."""
    
    def __init__(self, public_key: str):
        self.public_key = public_key
    
    def verify_signature(self, body: str, signature: str, timestamp: str) -> bool:
        """Verify the Discord interaction signature."""
        try:
            return verify_key(body.encode(), signature, timestamp, self.public_key)
        except Exception:
            return False
    
    def handle_ping(self) -> Dict[str, Any]:
        """Handle PING interaction type."""
        return {
            "type": InteractionResponseType.PONG
        }
    
    def handle_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle APPLICATION_COMMAND interaction type."""
        command_name = interaction.get("data", {}).get("name")
        
        if command_name == "ping":
            return self._ping_command(interaction)
        elif command_name == "login":
            return self._login_command(interaction)
        elif command_name == "start-shift":
            return self._start_shift_command(interaction)
        elif command_name == "end-shift":
            return self._end_shift_command(interaction)
        elif command_name == "shift-status":
            return self._shift_status_command(interaction)
        else:
            return {
                "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {
                    "content": f"Unknown command: {command_name}",
                    "flags": 64
                }
            }
    
    def _ping_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping command."""
        return {
            "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "embeds": [{
                    "title": "🏓 Pong!",
                    "description": "Bot is running on Cloudflare Workers!",
                    "color": 0xBEBEFE
                }]
            }
        }
    
    def _login_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle login command - deferred to process async."""
        return {
            "type": InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "flags": 64
            }
        }
    
    def _start_shift_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start-shift command - deferred to process async."""
        return {
            "type": InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "flags": 64
            }
        }
    
    def _end_shift_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle end-shift command - deferred to process async."""
        return {
            "type": InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "flags": 64
            }
        }
    
    def _shift_status_command(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shift-status command - deferred to process async."""
        return {
            "type": InteractionResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {
                "flags": 64
            }
        }
    
    def process_interaction(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Process the interaction and return appropriate response."""
        interaction_type = interaction.get("type")
        
        if interaction_type == InteractionType.PING:
            return self.handle_ping()
        elif interaction_type == InteractionType.APPLICATION_COMMAND:
            return self.handle_command(interaction)
        else:
            return {
                "type": InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
                "data": {
                    "content": "Unsupported interaction type",
                    "flags": 64
                }
            }


async def handle_request(request):
    """
    Main request handler for Cloudflare Workers.
    
    This function processes incoming Discord interactions.
    """
    public_key = os.getenv("DISCORD_PUBLIC_KEY")
    
    if not public_key:
        return Response(
            json.dumps({"error": "Missing DISCORD_PUBLIC_KEY"}),
            status=500,
            headers={"Content-Type": "application/json"}
        )
    
    if request.method != "POST":
        return Response(
            json.dumps({"error": "Method not allowed"}),
            status=405,
            headers={"Content-Type": "application/json"}
        )
    
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")
    
    if not signature or not timestamp:
        return Response(
            json.dumps({"error": "Missing signature headers"}),
            status=401,
            headers={"Content-Type": "application/json"}
        )
    
    body = await request.text()
    
    handler = DiscordInteractionHandler(public_key)
    
    if not handler.verify_signature(body, signature, timestamp):
        return Response(
            json.dumps({"error": "Invalid signature"}),
            status=401,
            headers={"Content-Type": "application/json"}
        )
    
    try:
        interaction = json.loads(body)
        response_data = handler.process_interaction(interaction)
        
        return Response(
            json.dumps(response_data),
            status=200,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        return Response(
            json.dumps({"error": f"Internal error: {str(e)}"}),
            status=500,
            headers={"Content-Type": "application/json"}
        )


class Response:
    """Simple Response class for compatibility."""
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}
