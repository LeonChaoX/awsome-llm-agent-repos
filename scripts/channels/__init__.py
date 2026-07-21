"""Built-in notification channel registry."""

from .base import Channel, NotificationError
from .discord import DiscordChannel
from .feishu import FeishuChannel
from .generic import GenericWebhookChannel
from .slack import SlackChannel
from .telegram import TelegramChannel
from .wecom import WeComChannel


CHANNELS: dict[str, type[Channel]] = {
    channel.name: channel
    for channel in (
        FeishuChannel,
        SlackChannel,
        TelegramChannel,
        WeComChannel,
        DiscordChannel,
        GenericWebhookChannel,
    )
}

__all__ = ["CHANNELS", "Channel", "NotificationError"]
