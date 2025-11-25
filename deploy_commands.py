"""
Command deployment script for Discord bot.
This script registers slash commands with Discord API without running the full bot.
Useful for Cloudflare Workers deployment where you need to register commands separately.
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")

if not DISCORD_TOKEN or not APPLICATION_ID:
    print("Error: TOKEN and APPLICATION_ID must be set in .env file")
    sys.exit(1)

COMMANDS = [
    {
        "name": "ping",
        "description": "Check if the bot is alive.",
        "type": 1
    },
    {
        "name": "login",
        "description": "Link your PocketBase auth key so you can use the shift commands.",
        "type": 1,
        "options": [
            {
                "name": "auth_key",
                "description": "Your PocketBase auth key from the staff portal.",
                "type": 3,
                "required": True
            }
        ]
    },
    {
        "name": "start-shift",
        "description": "Start your shift and log it in PocketBase.",
        "type": 1
    },
    {
        "name": "end-shift",
        "description": "End your active shift and record it in PocketBase.",
        "type": 1
    },
    {
        "name": "shift-status",
        "description": "Check your current shift or view the most recent shift on record.",
        "type": 1
    },
    {
        "name": "help",
        "description": "List all commands the bot has loaded.",
        "type": 1
    },
    {
        "name": "botinfo",
        "description": "Get some useful (or not) information about the bot.",
        "type": 1
    },
    {
        "name": "serverinfo",
        "description": "Get some useful (or not) information about the server.",
        "type": 1
    },
    {
        "name": "invite",
        "description": "Get the invite link of the bot to be able to invite it.",
        "type": 1
    },
    {
        "name": "server",
        "description": "Get the invite link of the discord server of the bot for some support.",
        "type": 1
    },
    {
        "name": "8ball",
        "description": "Ask any question to the bot.",
        "type": 1,
        "options": [
            {
                "name": "question",
                "description": "The question you want to ask.",
                "type": 3,
                "required": True
            }
        ]
    },
    {
        "name": "bitcoin",
        "description": "Get the current price of bitcoin.",
        "type": 1
    },
    {
        "name": "feedback",
        "description": "Submit a feedback for the owners of the bot.",
        "type": 1
    }
]


def register_commands_globally():
    """Register commands globally (takes up to 1 hour to propagate)."""
    url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }

    print(f"Registering {len(COMMANDS)} commands globally...")
    
    for command in COMMANDS:
        response = requests.post(url, json=command, headers=headers)
        if response.status_code in (200, 201):
            print(f"✓ Registered command: {command['name']}")
        else:
            print(f"✗ Failed to register {command['name']}: {response.text}")
    
    print("\nCommands registered! Global commands may take up to 1 hour to appear.")


def register_commands_to_guild(guild_id: str):
    """Register commands to a specific guild (instant)."""
    url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{guild_id}/commands"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }

    print(f"Registering {len(COMMANDS)} commands to guild {guild_id}...")
    
    for command in COMMANDS:
        response = requests.post(url, json=command, headers=headers)
        if response.status_code in (200, 201):
            print(f"✓ Registered command: {command['name']}")
        else:
            print(f"✗ Failed to register {command['name']}: {response.text}")
    
    print("\nCommands registered to guild! They should appear immediately.")


def delete_all_global_commands():
    """Delete all globally registered commands."""
    url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch commands: {response.text}")
        return

    commands = response.json()
    print(f"Found {len(commands)} global commands to delete...")

    for command in commands:
        delete_url = f"{url}/{command['id']}"
        response = requests.delete(delete_url, headers=headers)
        if response.status_code == 204:
            print(f"✓ Deleted command: {command['name']}")
        else:
            print(f"✗ Failed to delete {command['name']}: {response.text}")

    print("\nAll global commands deleted!")


def delete_all_guild_commands(guild_id: str):
    """Delete all commands registered to a specific guild."""
    url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{guild_id}/commands"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch commands: {response.text}")
        return

    commands = response.json()
    print(f"Found {len(commands)} guild commands to delete...")

    for command in commands:
        delete_url = f"{url}/{command['id']}"
        response = requests.delete(delete_url, headers=headers)
        if response.status_code == 204:
            print(f"✓ Deleted command: {command['name']}")
        else:
            print(f"✗ Failed to delete {command['name']}: {response.text}")

    print(f"\nAll guild commands deleted from guild {guild_id}!")


def main():
    """Main entry point."""
    print("Discord Command Deployment Tool")
    print("=" * 50)
    print("1. Register commands globally (1 hour propagation)")
    print("2. Register commands to guild (instant)")
    print("3. Delete all global commands")
    print("4. Delete all guild commands")
    print("0. Exit")
    print("=" * 50)
    
    choice = input("\nEnter your choice: ").strip()
    
    if choice == "1":
        register_commands_globally()
    elif choice == "2":
        guild_id = input("Enter guild ID: ").strip()
        if guild_id:
            register_commands_to_guild(guild_id)
        else:
            print("Guild ID cannot be empty!")
    elif choice == "3":
        confirm = input("Are you sure you want to delete all global commands? (yes/no): ").strip().lower()
        if confirm == "yes":
            delete_all_global_commands()
        else:
            print("Cancelled.")
    elif choice == "4":
        guild_id = input("Enter guild ID: ").strip()
        if guild_id:
            confirm = input(f"Are you sure you want to delete all commands from guild {guild_id}? (yes/no): ").strip().lower()
            if confirm == "yes":
                delete_all_guild_commands(guild_id)
            else:
                print("Cancelled.")
        else:
            print("Guild ID cannot be empty!")
    elif choice == "0":
        print("Exiting...")
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()
