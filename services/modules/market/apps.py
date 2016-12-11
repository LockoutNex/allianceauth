from __future__ import unicode_literals

from django.apps import AppConfig


class MarketServiceConfig(AppConfig):
    name = 'market'

    def ready(self):
        import services.signals