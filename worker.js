/**
 * Cloudflare Workers entry point for Discord bot using Interactions API.
 * This allows the bot to run on Cloudflare Workers as a webhook-based application.
 */

import { verifyKey } from 'discord-interactions';

const COMMAND_HANDLERS = {
  ping: handlePingCommand,
  login: handleLoginCommand,
  'start-shift': handleStartShiftCommand,
  'end-shift': handleEndShiftCommand,
  'shift-status': handleShiftStatusCommand,
};

/**
 * Main request handler for Cloudflare Workers
 */
export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    const signature = request.headers.get('X-Signature-Ed25519');
    const timestamp = request.headers.get('X-Signature-Timestamp');

    if (!signature || !timestamp) {
      return new Response('Missing signature headers', { status: 401 });
    }

    const body = await request.text();

    // Verify the request signature
    const isValidRequest = verifyKey(
      body,
      signature,
      timestamp,
      env.DISCORD_PUBLIC_KEY
    );

    if (!isValidRequest) {
      return new Response('Invalid signature', { status: 401 });
    }

    const interaction = JSON.parse(body);

    // Handle PING (Discord verification)
    if (interaction.type === 1) {
      return jsonResponse({ type: 1 });
    }

    // Handle APPLICATION_COMMAND
    if (interaction.type === 2) {
      const commandName = interaction.data.name;
      const handler = COMMAND_HANDLERS[commandName];

      if (handler) {
        return handler(interaction, env);
      }

      return jsonResponse({
        type: 4,
        data: {
          content: `Unknown command: ${commandName}`,
          flags: 64, // Ephemeral
        },
      });
    }

    return jsonResponse({
      type: 4,
      data: {
        content: 'Unsupported interaction type',
        flags: 64,
      },
    });
  },
};

/**
 * Handle ping command
 */
function handlePingCommand(interaction, env) {
  return jsonResponse({
    type: 4,
    data: {
      embeds: [
        {
          title: '🏓 Pong!',
          description: 'Bot is running on Cloudflare Workers!',
          color: 0xbebefe,
        },
      ],
    },
  });
}

/**
 * Handle login command - processes auth key linking
 */
async function handleLoginCommand(interaction, env) {
  const authKey = interaction.data.options?.find(opt => opt.name === 'auth_key')?.value;
  
  if (!authKey) {
    return jsonResponse({
      type: 4,
      data: {
        content: 'Auth key is required',
        flags: 64,
      },
    });
  }

  return featureComingSoonResponse('login');
}

/**
 * Handle start-shift command
 */
async function handleStartShiftCommand(interaction, env) {
  return featureComingSoonResponse('start-shift');
}

/**
 * Handle end-shift command
 */
async function handleEndShiftCommand(interaction, env) {
  return featureComingSoonResponse('end-shift');
}

/**
 * Handle shift-status command
 */
async function handleShiftStatusCommand(interaction, env) {
  return featureComingSoonResponse('shift-status');
}

/**
 * Helper function to create JSON responses
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

/**
 * Placeholder response for features not yet implemented in Workers
 */
function featureComingSoonResponse(commandName) {
  return jsonResponse({
    type: 4,
    data: {
      embeds: [
        {
          title: 'Feature in Development',
          description: `The \`${commandName}\` command is available in the traditional bot deployment. Full Cloudflare Workers implementation coming soon!`,
          color: 0xbebefe,
          footer: {
            text: 'Use the traditional bot (bot.py) for full functionality'
          }
        },
      ],
      flags: 64,
    },
  });
}
