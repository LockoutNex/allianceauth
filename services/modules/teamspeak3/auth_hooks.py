from __future__ import unicode_literals

from django.conf import settings
from django.template.loader import render_to_string

from services.hooks import ServicesHook
from alliance_auth import hooks

from .urls import urlpatterns
from .tasks import Teamspeak3Tasks

import logging

logger = logging.getLogger(__name__)


class Teamspeak3Service(ServicesHook):
    def __init__(self):
        ServicesHook.__init__(self)
        self.name = 'teamspeak3'
        self.urlpatterns = urlpatterns
        self.service_ctrl_template = 'registered/teamspeak3_service_ctrl.html'

    def delete_user(self, user, notify_user=False):
        logger.debug('Deleting user %s %s account' % (user, self.name))
        return Teamspeak3Tasks.delete_user(user, notify_user=notify_user)

    def update_groups(self, user):
        logger.debug('Updating %s groups for %s' % (self.name, user))
        Teamspeak3Tasks.update_groups.delay(user.pk)

    def validate_user(self, user):
        logger.debug('Validating user %s %s account' % (user, self.name))
        if Teamspeak3Tasks.has_account(user) and not self.service_active_for_user(user):
            self.delete_user(user, notify_user=True)

    def update_all_groups(self):
        logger.debug('Update all %s groups called' % self.name)
        Teamspeak3Tasks.update_all_groups.delay()

    def service_enabled_members(self):
        return settings.ENABLE_AUTH_TEAMSPEAK3 or False

    def service_enabled_blues(self):
        return settings.ENABLE_BLUE_TEAMSPEAK3 or False

    def render_services_ctrl(self, request):
        authinfo = {'teamspeak3_uid': '',
                    'teamspeak3_perm_key': '',}
        if Teamspeak3Tasks.has_account(request.user):
            authinfo['teamspeak3_uid'] = request.user.teamspeak3.uid
            authinfo['teamspeak3_perm_key'] = request.user.teamspeak3.perm_key

        return render_to_string(self.service_ctrl_template, {
            'authinfo': authinfo,
        }, request=request)


@hooks.register('services_hook')
def register_service():
    return Teamspeak3Service()
