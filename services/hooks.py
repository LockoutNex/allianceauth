from __future__ import unicode_literals

from authentication.states import MEMBER_STATE, BLUE_STATE
from authentication.models import AuthServicesInfo


class ServicesHook:
    """
    Abstract base class for creating a compatible services
    hook. Decorate with @register('services_hook') to have the
    services module registered for callbacks. Must be in
    auth_hook(.py) sub module
    """
    def __init__(self):
        self.name = 'Undefined'
        self.urlpatterns = []
        self.service_ctrl_template = 'registered/services_ctrl.html'

    @property
    def title(self):
        """
        A nicely formatted title of the service, for client facing
        display.
        :return: str
        """
        return self.name.title()

    def delete_user(self, user, notify_user=False):
        """
        Delete the users service account, optionally notify them
        that the service has been disabled
        :param user: Django.contrib.auth.models.User
        :param notify_user: Whether the service should sent a
        notification to the user about the disabling of their
        service account.
        :return: True if the service account has been disabled,
        or False if it doesnt exist.
        """
        pass

    def validate_user(self, user):
        pass

    def update_groups(self, user):
        """
        Update the users group membership
        :param user: Django.contrib.auth.models.User
        :return: None
        """
        pass

    def update_all_groups(self):
        """
        Iterate through and update all users groups
        :return: None
        """
        pass

    def service_enabled_members(self):
        """
        Return setting config for service enabled for members
        :return: bool True if enabled
        """
        return False

    def service_enabled_blues(self):
        """
        Return setting config for service enabled for Blues
        :return: bool True if enabled
        """
        return False

    def service_active_for_user(self, user):
        state = AuthServicesInfo.objects.get_or_create(user=user)[0].state
        return (
            (state == MEMBER_STATE and self.service_enabled_members()) or
            (state == BLUE_STATE and self.service_enabled_blues())
        )

    def show_service_ctrl(self, user, state):
        """
        Whether the service control should be displayed to the given user
        who has the given service state. Usually this function wont
        require overloading.
        :param user: django.contrib.auth.models.User
        :param state: auth user state
        :return: bool True if the service should be shown
        """
        return (self.service_enabled_members() and (
            state == MEMBER_STATE or user.is_superuser)) or (
                self.service_enabled_blues() and (state == BLUE_STATE or user.is_superuser))

    def render_services_ctrl(self, request):
        """
        Render the services control template row
        :param request:
        :return:
        """
        return ''

    class Urls:
        def __init__(self):
            self.auth_activate = ''
            self.auth_set_password = ''
            self.auth_reset_password = ''
            self.auth_deactivate = ''
