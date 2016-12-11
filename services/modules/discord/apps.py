from __future__ import unicode_literals

from django.apps import AppConfig


class DiscordServiceConfig(AppConfig):
    name = 'discord'

    def ready(self):
        import services.signals