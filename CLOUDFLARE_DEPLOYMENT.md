# Cloudflare Workers Deployment Guide

This guide explains how to deploy the Discord bot to Cloudflare Workers using Discord's Interactions API (webhook-based approach).

## Overview

Cloudflare Workers is a serverless platform that allows you to run code at the edge. Unlike traditional Discord bots that maintain a WebSocket connection to Discord, the Workers deployment uses Discord's Interactions API, which sends HTTP POST requests to your worker endpoint.

## Prerequisites

1. A Discord application and bot created at https://discord.com/developers/applications
2. A Cloudflare account (free tier works)
3. Node.js and npm installed (for deploying the worker)
4. Wrangler CLI: `npm install -g wrangler`

## Setup Steps

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Secrets

Set the following secrets using Wrangler:

```bash
# Your Discord application's public key (found in Discord Developer Portal)
wrangler secret put DISCORD_PUBLIC_KEY

# Your Discord bot token
wrangler secret put DISCORD_BOT_TOKEN

# Your PocketBase instance URL (if using PocketBase integration)
wrangler secret put POCKETBASE_URL
```

### 3. Deploy to Cloudflare Workers

```bash
# Deploy to production
wrangler deploy

# Or run locally for testing
wrangler dev
```

### 4. Configure Discord Interactions Endpoint

After deployment, you'll get a URL like: `https://discord-bot.your-subdomain.workers.dev`

1. Go to your Discord application in the [Developer Portal](https://discord.com/developers/applications)
2. Navigate to "General Information"
3. Set the "Interactions Endpoint URL" to your worker URL
4. Discord will send a PING request to verify the endpoint

### 5. Register Commands

You have two options to register/sync commands:

#### Option A: Use the existing bot (recommended for initial setup)

Run the bot normally and use the sync command:
```bash
python main.py
```

Then in Discord, use the prefix command:
```
!sync global
```

This will register all commands globally with Discord.

#### Option B: Use a deployment script

Create a script to register commands directly with Discord API (see `deploy_commands.py` below).

## Architecture Differences

### Traditional Bot (bot.py)
- ✅ Maintains persistent WebSocket connection
- ✅ Can listen to all gateway events
- ✅ Can have background tasks
- ❌ Requires always-running server
- ❌ Higher hosting costs for 24/7 uptime

### Cloudflare Workers (worker.js)
- ✅ Serverless - only runs when needed
- ✅ Free tier available (100,000 requests/day)
- ✅ Global edge network for low latency
- ✅ Automatic scaling
- ❌ No persistent connections
- ❌ Only receives interaction events
- ❌ Execution time limits (CPU time, wall time)

## File Structure

- `worker.js` - Main Cloudflare Workers handler (JavaScript)
- `worker.py` - Alternative Python-based worker (if using Python Workers)
- `wrangler.toml` - Cloudflare Workers configuration
- `package.json` - Node.js dependencies

## Command Registration Script

Create `deploy_commands.py` to register commands without running the full bot:

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")

# Define your commands
commands = [
    {
        "name": "ping",
        "description": "Check if the bot is alive.",
        "type": 1
    },
    {
        "name": "login",
        "description": "Link your PocketBase auth key.",
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
        "description": "Check your current shift status.",
        "type": 1
    }
]

# Register commands globally
url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"
headers = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
    "Content-Type": "application/json"
}

for command in commands:
    response = requests.post(url, json=command, headers=headers)
    if response.status_code == 200 or response.status_code == 201:
        print(f"✓ Registered command: {command['name']}")
    else:
        print(f"✗ Failed to register {command['name']}: {response.text}")
```

## Troubleshooting

### Command Not Found Error

If you see `CommandNotFound` errors, it means Discord has commands registered that don't exist in your code. To fix:

1. Use the unsync command to clear old commands:
   ```
   !unsync global
   ```

2. Then sync the current commands:
   ```
   !sync global
   ```

### CommandSignatureMismatch Error

This means the command signature in your code differs from what Discord has registered. To fix:

1. Check that all command parameters match
2. Resync commands:
   ```
   !sync global
   ```

### Invalid Signature Error

If your worker returns "Invalid signature", check:
- DISCORD_PUBLIC_KEY is set correctly
- The public key is from your Discord application's "General Information" page
- Not confused with the bot token

## Migrating from Traditional Bot to Workers

1. Deploy both versions initially
2. Test the Workers deployment with a test server
3. Update the Interactions Endpoint URL in Discord
4. Monitor logs for any issues
5. Shut down the traditional bot once Workers is stable

## Data Storage

For persistent data storage with Workers, consider:

- **Cloudflare D1**: SQLite-compatible database
- **Cloudflare KV**: Key-value store for simple data
- **External Database**: Connect to PostgreSQL, MySQL, etc. via HTTP
- **Cloudflare Durable Objects**: For complex state management

Update `wrangler.toml` to configure these services.

## Cost Estimation

Cloudflare Workers Free Tier:
- 100,000 requests/day
- 10ms CPU time per request

Most Discord bots will fit comfortably within the free tier.

## Additional Resources

- [Cloudflare Workers Documentation](https://developers.cloudflare.com/workers/)
- [Discord Interactions API](https://discord.com/developers/docs/interactions/receiving-and-responding)
- [Wrangler CLI Reference](https://developers.cloudflare.com/workers/wrangler/)
