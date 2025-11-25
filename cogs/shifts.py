from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from pocketbase_client import (
    PocketBaseAuthenticationError,
    PocketBaseClient,
    PocketBaseError,
)

SUCCESS_COLOR = 0xBEBEFE
ERROR_COLOR = 0xE02B2B
MAX_DURATION_MINUTES = 360


class Shifts(commands.Cog, name="shifts"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="login",
        description="Link your PocketBase auth key so you can use the shift commands.",
    )
    @app_commands.describe(auth_key="Your PocketBase auth key from the staff portal.")
    async def login(self, interaction: discord.Interaction, auth_key: str) -> None:
        client = await self._require_client(interaction)
        if client is None:
            return

        await interaction.response.defer(ephemeral=True)
        try:
            user_record = await client.get_user_by_discord_id(auth_key, interaction.user.id)
        except PocketBaseAuthenticationError as error:
            await interaction.followup.send(
                embed=self._error_embed(str(error)),
                ephemeral=True,
            )
            return
        except PocketBaseError as error:
            await interaction.followup.send(
                embed=self._error_embed(str(error)),
                ephemeral=True,
            )
            return

        discord_linked_id = user_record.get("discord_user_id")
        if str(discord_linked_id) != str(interaction.user.id):
            await interaction.followup.send(
                embed=self._error_embed(
                    "That auth key belongs to a different Discord user. Please make sure you copied your own key."
                ),
                ephemeral=True,
            )
            return

        await self.bot.database.set_pocketbase_token(interaction.user.id, auth_key)

        embed = discord.Embed(
            title="PocketBase linked",
            description="Your auth key has been stored securely. You can now use the shift commands.",
            color=SUCCESS_COLOR,
        )
        embed.add_field(
            name="PocketBase user",
            value=user_record.get("name") or user_record.get("id"),
            inline=False,
        )
        role = user_record.get("role")
        if role:
            embed.add_field(name="Role", value=role, inline=False)
        embed.set_footer(text="You can update your auth key at any time by running /login again.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="start-shift", description="Start your shift and log it in PocketBase.")
    async def start_shift(self, interaction: discord.Interaction) -> None:
        client = await self._require_client(interaction)
        if client is None:
            return

        auth_token = await self._require_auth_token(interaction)
        if auth_token is None:
            return

        await interaction.response.defer(ephemeral=True)
        try:
            user_record = await client.get_user_by_discord_id(auth_token, interaction.user.id)
            user_id = user_record.get("id")
            if not user_id:
                raise PocketBaseError("PocketBase did not return your user ID.")

            active_shift = await client.get_active_shift(auth_token, user_id)
            if active_shift:
                start_time = active_shift.get("start_time")
                start_dt = self._parse_timestamp(start_time) if start_time else None
                embed = self._error_embed(
                    "You already have an active shift. Please end it before starting a new one."
                )
                if start_dt:
                    embed.add_field(
                        name="Current shift started",
                        value=self._format_discord_timestamp(start_dt),
                        inline=False,
                    )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            shift_record = await client.create_shift(auth_token, user_id)
            start_time = shift_record.get("start_time")
            start_dt = self._parse_timestamp(start_time) if start_time else self._now()
            embed = discord.Embed(
                title="Shift started",
                description=f"{interaction.user.mention}, your shift has been logged.",
                color=SUCCESS_COLOR,
            )
            embed.add_field(
                name="Start time",
                value=self._format_discord_timestamp(start_dt),
                inline=False,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except PocketBaseAuthenticationError as error:
            await self._handle_auth_error(interaction, error)
        except PocketBaseError as error:
            await interaction.followup.send(
                embed=self._error_embed(str(error)), ephemeral=True
            )

    @app_commands.command(name="end-shift", description="End your active shift and record it in PocketBase.")
    async def end_shift(self, interaction: discord.Interaction) -> None:
        client = await self._require_client(interaction)
        if client is None:
            return

        auth_token = await self._require_auth_token(interaction)
        if auth_token is None:
            return

        await interaction.response.defer(ephemeral=True)
        try:
            user_record = await client.get_user_by_discord_id(auth_token, interaction.user.id)
            user_id = user_record.get("id")
            if not user_id:
                raise PocketBaseError("PocketBase did not return your user ID.")

            active_shift = await client.get_active_shift(auth_token, user_id)
            if not active_shift:
                await interaction.followup.send(
                    embed=self._error_embed("You do not have an active shift to end."),
                    ephemeral=True,
                )
                return

            start_time = active_shift.get("start_time")
            start_dt = self._parse_timestamp(start_time) if start_time else self._now()
            end_dt = self._now()
            elapsed_minutes = self._minutes_between(start_dt, end_dt)
            recorded_minutes = min(elapsed_minutes, MAX_DURATION_MINUTES)

            await client.complete_shift(
                auth_token,
                active_shift["id"],
                self._format_pocketbase_timestamp(end_dt),
                recorded_minutes,
            )

            embed = discord.Embed(
                title="Shift completed",
                description=f"{interaction.user.mention}, your shift has been closed.",
                color=SUCCESS_COLOR,
            )
            embed.add_field(
                name="Start time",
                value=self._format_discord_timestamp(start_dt),
                inline=False,
            )
            embed.add_field(
                name="End time",
                value=self._format_discord_timestamp(end_dt),
                inline=False,
            )
            duration_text = self._format_minutes(recorded_minutes)
            if recorded_minutes < elapsed_minutes:
                duration_text += " (capped at 360 minutes)"
            embed.add_field(name="Duration", value=duration_text, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except PocketBaseAuthenticationError as error:
            await self._handle_auth_error(interaction, error)
        except PocketBaseError as error:
            await interaction.followup.send(
                embed=self._error_embed(str(error)), ephemeral=True
            )

    @app_commands.command(
        name="shift-status",
        description="Check your current shift or view the most recent shift on record.",
    )
    async def shift_status(self, interaction: discord.Interaction) -> None:
        client = await self._require_client(interaction)
        if client is None:
            return

        auth_token = await self._require_auth_token(interaction)
        if auth_token is None:
            return

        await interaction.response.defer(ephemeral=True)
        try:
            user_record = await client.get_user_by_discord_id(auth_token, interaction.user.id)
            user_id = user_record.get("id")
            if not user_id:
                raise PocketBaseError("PocketBase did not return your user ID.")

            active_shift = await client.get_active_shift(auth_token, user_id)
            if active_shift:
                start_time = active_shift.get("start_time")
                start_dt = self._parse_timestamp(start_time) if start_time else self._now()
                elapsed_minutes = self._minutes_between(start_dt, self._now())
                embed = discord.Embed(
                    title="Shift status",
                    description="You currently have an active shift.",
                    color=SUCCESS_COLOR,
                )
                embed.add_field(
                    name="Started",
                    value=self._format_discord_timestamp(start_dt),
                    inline=False,
                )
                embed.add_field(
                    name="Elapsed",
                    value=self._format_minutes(elapsed_minutes),
                    inline=False,
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            latest_shift = await client.get_latest_shift(auth_token, user_id)
            if latest_shift:
                embed = discord.Embed(
                    title="Shift status",
                    description="You do not have an active shift right now.",
                    color=SUCCESS_COLOR,
                )
                start_time = latest_shift.get("start_time")
                end_time = latest_shift.get("end_time")
                if start_time:
                    start_dt = self._parse_timestamp(start_time)
                    embed.add_field(
                        name="Last shift started",
                        value=self._format_discord_timestamp(start_dt),
                        inline=False,
                    )
                if end_time:
                    end_dt = self._parse_timestamp(end_time)
                    embed.add_field(
                        name="Last shift ended",
                        value=self._format_discord_timestamp(end_dt),
                        inline=False,
                    )
                duration = latest_shift.get("duration_minutes")
                if duration is not None:
                    embed.add_field(
                        name="Recorded duration",
                        value=self._format_minutes(int(duration)),
                        inline=False,
                    )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            await interaction.followup.send(
                embed=discord.Embed(
                    title="Shift status",
                    description="You have not logged any shifts yet.",
                    color=SUCCESS_COLOR,
                ),
                ephemeral=True,
            )
        except PocketBaseAuthenticationError as error:
            await self._handle_auth_error(interaction, error)
        except PocketBaseError as error:
            await interaction.followup.send(
                embed=self._error_embed(str(error)), ephemeral=True
            )

    async def _require_client(
        self, interaction: discord.Interaction
    ) -> Optional[PocketBaseClient]:
        client = self._get_client()
        if client is None:
            await interaction.response.send_message(
                embed=self._error_embed(
                    "The PocketBase integration is not configured. Please contact a bot administrator."
                ),
                ephemeral=True,
            )
            return None
        return client

    async def _require_auth_token(self, interaction: discord.Interaction) -> Optional[str]:
        token = await self.bot.database.get_pocketbase_token(interaction.user.id)
        if token:
            return token

        await interaction.response.send_message(
            embed=self._error_embed(
                "Please link your PocketBase auth key first by running /login."
            ),
            ephemeral=True,
        )
        return None

    async def _handle_auth_error(
        self, interaction: discord.Interaction, error: PocketBaseAuthenticationError
    ) -> None:
        await self.bot.database.clear_pocketbase_token(interaction.user.id)
        await interaction.followup.send(
            embed=self._error_embed(f"{error} Your saved auth key has been removed."),
            ephemeral=True,
        )

    def _get_client(self) -> Optional[PocketBaseClient]:
        client = getattr(self.bot, "pocketbase", None)
        if client and client.is_configured:
            return client
        return None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _format_discord_timestamp(dt: datetime) -> str:
        timestamp = int(dt.timestamp())
        return f"<t:{timestamp}:F> (<t:{timestamp}:R>)"

    @staticmethod
    def _format_pocketbase_timestamp(dt: datetime) -> str:
        return (
            dt.astimezone(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _minutes_between(start: datetime, end: datetime) -> int:
        delta = end - start
        seconds = max(0, int(delta.total_seconds()))
        minutes = seconds // 60
        return minutes if minutes >= 1 else 1

    @staticmethod
    def _format_minutes(minutes: int) -> str:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        if not value:
            raise PocketBaseError("PocketBase did not return a timestamp for this shift.")
        normalized = value.replace(" ", "T")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(normalized).astimezone(timezone.utc)
        except ValueError as exc:
            raise PocketBaseError(
                "Received an unexpected timestamp format from PocketBase."
            ) from exc

    @staticmethod
    def _error_embed(message: str) -> discord.Embed:
        return discord.Embed(description=message, color=ERROR_COLOR)


async def setup(bot) -> None:
    await bot.add_cog(Shifts(bot))
