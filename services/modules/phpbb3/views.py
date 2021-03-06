from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from authentication.decorators import members_and_blues
from eveonline.managers import EveManager
from services.forms import ServicePasswordForm

from .manager import Phpbb3Manager
from .tasks import Phpbb3Tasks
from .models import Phpbb3User

import logging

logger = logging.getLogger(__name__)


@login_required
@members_and_blues()
def activate_forum(request):
    logger.debug("activate_forum called by user %s" % request.user)
    # Valid now we get the main characters
    character = EveManager.get_main_character(request.user)
    logger.debug("Adding phpbb user for user %s with main character %s" % (request.user, character))
    result = Phpbb3Manager.add_user(character.character_name, request.user.email, ['REGISTERED'],
                                    character.character_id)
    # if empty we failed
    if result[0] != "":
        Phpbb3User.objects.update_or_create(user=request.user, defaults={'username': result[0]})
        logger.debug("Updated authserviceinfo for user %s with forum credentials. Updating groups." % request.user)
        Phpbb3Tasks.update_groups.delay(request.user.pk)
        logger.info("Successfully activated forum for user %s" % request.user)
        messages.success(request, 'Activated forum account.')
        credentials = {
            'username': result[0],
            'password': result[1],
        }
        return render(request, 'registered/service_credentials.html',
                      context={'credentials': credentials, 'service': 'Forum'})
    else:
        logger.error("Unsuccessful attempt to activate forum for user %s" % request.user)
        messages.error(request, 'An error occurred while processing your forum account.')
    return redirect("auth_services")


@login_required
@members_and_blues()
def deactivate_forum(request):
    logger.debug("deactivate_forum called by user %s" % request.user)
    # false we failed
    if Phpbb3Tasks.delete_user(request.user):
        logger.info("Successfully deactivated forum for user %s" % request.user)
        messages.success(request, 'Deactivated forum account.')
    else:
        logger.error("Unsuccessful attempt to activate forum for user %s" % request.user)
        messages.error(request, 'An error occurred while processing your forum account.')
    return redirect("auth_services")


@login_required
@members_and_blues()
def reset_forum_password(request):
    logger.debug("reset_forum_password called by user %s" % request.user)
    if Phpbb3Tasks.has_account(request.user):
        character = EveManager.get_main_character(request.user)
        result = Phpbb3Manager.update_user_password(request.user.phpbb3.username, character.character_id)
        # false we failed
        if result != "":
            logger.info("Successfully reset forum password for user %s" % request.user)
            messages.success(request, 'Reset forum password.')
            credentials = {
                'username': request.user.phpbb3.username,
                'password': result,
            }
            return render(request, 'registered/service_credentials.html',
                          context={'credentials': credentials, 'service': 'Forum'})

    logger.error("Unsuccessful attempt to reset forum password for user %s" % request.user)
    messages.error(request, 'An error occurred while processing your forum account.')
    return redirect("auth_services")


@login_required
@members_and_blues()
def set_forum_password(request):
    logger.debug("set_forum_password called by user %s" % request.user)
    if request.method == 'POST':
        logger.debug("Received POST request with form.")
        form = ServicePasswordForm(request.POST)
        logger.debug("Form is valid: %s" % form.is_valid())
        if form.is_valid() and Phpbb3Tasks.has_account(request.user):
            password = form.cleaned_data['password']
            logger.debug("Form contains password of length %s" % len(password))
            character = EveManager.get_main_character(request.user)
            result = Phpbb3Manager.update_user_password(request.user.phpbb3.username, character.character_id,
                                                        password=password)
            if result != "":
                logger.info("Successfully set forum password for user %s" % request.user)
                messages.success(request, 'Set forum password.')
            else:
                logger.error("Failed to install custom forum password for user %s" % request.user)
                messages.error(request, 'An error occurred while processing your forum account.')
            return redirect("auth_services")
    else:
        logger.debug("Request is not type POST - providing empty form.")
        form = ServicePasswordForm()

    logger.debug("Rendering form for user %s" % request.user)
    context = {'form': form, 'service': 'Forum'}
    return render(request, 'registered/service_password.html', context=context)
