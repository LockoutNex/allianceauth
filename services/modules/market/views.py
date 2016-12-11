from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from authentication.decorators import members_and_blues
from authentication.managers import AuthServicesInfoManager
from authentication.models import AuthServicesInfo
from services.forms import ServicePasswordForm
from eveonline.managers import EveManager

from .manager import marketManager


import logging

logger = logging.getLogger(__name__)


@login_required
@members_and_blues()
def activate_market(request):
    logger.debug("activate_market called by user %s" % request.user)
    authinfo = AuthServicesInfo.objects.get_or_create(user=request.user)[0]
    # Valid now we get the main characters
    character = EveManager.get_character_by_id(authinfo.main_char_id)
    logger.debug("Adding market user for user %s with main character %s" % (request.user, character))
    result = marketManager.add_user(character.character_name, request.user.email, authinfo.main_char_id,
                                    character.character_name)
    # if empty we failed
    if result[0] != "":
        AuthServicesInfoManager.update_user_market_info(result[0], request.user)
        logger.debug("Updated authserviceinfo for user %s with market credentials." % request.user)
        logger.info("Successfully activated market for user %s" % request.user)
        messages.success(request, 'Activated Alliance Market account.')
        credentials = {
            'username': result[0],
            'password': result[1],
        }
        return render(request, 'registered/service_credentials.html',
                      context={'credentials': credentials, 'service': 'Alliance Market'})
    else:
        logger.error("UnSuccessful attempt to activate market for user %s" % request.user)
        messages.error(request, 'An error occurred while processing your Alliance Market account.')
    return redirect("auth_services")


@login_required
@members_and_blues()
def deactivate_market(request):
    logger.debug("deactivate_market called by user %s" % request.user)
    authinfo = AuthServicesInfo.objects.get_or_create(user=request.user)[0]
    result = marketManager.disable_user(authinfo.market_username)
    # false we failed
    if result:
        AuthServicesInfoManager.update_user_market_info("", request.user)
        logger.info("Successfully deactivated market for user %s" % request.user)
        messages.success(request, 'Deactivated Alliance Market account.')
    else:
        logger.error("UnSuccessful attempt to activate market for user %s" % request.user)
        messages.error(request, 'An error occurred while processing your Alliance Market account.')
    return redirect("auth_services")


@login_required
@members_and_blues()
def reset_market_password(request):
    logger.debug("reset_market_password called by user %s" % request.user)
    authinfo = AuthServicesInfo.objects.get_or_create(user=request.user)[0]
    result = marketManager.update_user_password(authinfo.market_username)
    # false we failed
    if result != "":
        logger.info("Successfully reset market password for user %s" % request.user)
        messages.success(request, 'Reset Alliance Market password.')
        credentials = {
            'username': authinfo.market_username,
            'password': result,
        }
        return render(request, 'registered/service_credentials.html',
                      context={'credentials': credentials, 'service': 'Alliance Market'})
    else:
        logger.error("Unsuccessful attempt to reset market password for user %s" % request.user)
        messages.error(request, 'An error occurred while processing your Alliance Market account.')
    return redirect("auth_services")


@login_required
@members_and_blues()
def set_market_password(request):
    logger.debug("set_market_password called by user %s" % request.user)
    if request.method == 'POST':
        logger.debug("Received POST request with form.")
        form = ServicePasswordForm(request.POST)
        logger.debug("Form is valid: %s" % form.is_valid())
        if form.is_valid():
            password = form.cleaned_data['password']
            logger.debug("Form contains password of length %s" % len(password))
            authinfo = AuthServicesInfo.objects.get_or_create(user=request.user)[0]
            result = marketManager.update_custom_password(authinfo.market_username, password)
            if result != "":
                logger.info("Successfully reset market password for user %s" % request.user)
                messages.success(request, 'Set Alliance Market password.')
            else:
                logger.error("Failed to install custom market password for user %s" % request.user)
                messages.error(request, 'An error occurred while processing your Alliance Market account.')
            return redirect("auth_services")
    else:
        logger.debug("Request is not type POST - providing empty form.")
        form = ServicePasswordForm()

    logger.debug("Rendering form for user %s" % request.user)
    context = {'form': form, 'service': 'Market'}
    return render(request, 'registered/service_password.html', context=context)
