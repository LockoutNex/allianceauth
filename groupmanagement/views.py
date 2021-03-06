from __future__ import unicode_literals
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group
from django.contrib import messages
from notifications import notify
from django.utils.translation import ugettext_lazy as _
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from groupmanagement.managers import GroupManager
from groupmanagement.models import GroupRequest
from authentication.models import AuthServicesInfo
from eveonline.managers import EveManager

import logging

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_management(request):
    logger.debug("group_management called by user %s" % request.user)
    acceptrequests = []
    leaverequests = []

    if GroupManager.has_management_permission(request.user):
        # Full access
        group_requests = GroupRequest.objects.all()
    else:
        # Group specific leader
        group_requests = GroupRequest.objects.filter(group__authgroup__group_leaders__in=[request.user])

    for grouprequest in group_requests:
        if grouprequest.leave_request:
            leaverequests.append(grouprequest)
        else:
            acceptrequests.append(grouprequest)

    logger.debug("Providing user %s with %s acceptrequests and %s leaverequests." % (
        request.user, len(acceptrequests), len(leaverequests)))

    render_items = {'acceptrequests': acceptrequests, 'leaverequests': leaverequests}

    return render(request, 'registered/groupmanagement.html', context=render_items)


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_membership(request):
    logger.debug("group_membership called by user %s" % request.user)
    # Get all open and closed groups
    if GroupManager.has_management_permission(request.user):
        # Full access
        groups = GroupManager.get_joinable_groups()
    else:
        # Group leader specific
        groups = GroupManager.get_group_leaders_groups(request.user)

    groups = groups.exclude(authgroup__internal=True).annotate(num_members=Count('user')).order_by('name')

    render_items = {'groups': groups}

    return render(request, 'registered/groupmembership.html', context=render_items)


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_membership_list(request, group_id):
    logger.debug("group_membership_list called by user %s for group id %s" % (request.user, group_id))
    try:
        group = Group.objects.get(id=group_id)

        # Check its a joinable group i.e. not corp or internal
        # And the user has permission to manage it
        if not GroupManager.joinable_group(group) or not GroupManager.can_manage_group(request.user, group):
            logger.warning("User %s attempted to view the membership of group %s but permission was denied" %
                           (request.user, group_id))
            raise PermissionDenied

    except ObjectDoesNotExist:
        raise Http404("Group does not exist")

    members = list()

    for member in group.user_set.all().order_by('username'):
        authinfo = AuthServicesInfo.objects.get(user=member)

        members.append({
            'user': member,
            'main_char': EveManager.get_character_by_id(authinfo.main_char_id)
        })

    render_items = {'group': group, 'members': members}

    return render(request, 'registered/groupmembers.html', context=render_items)


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_membership_remove(request, group_id, user_id):
    logger.debug("group_membership_remove called by user %s for group id %s on user id %s" %
                 (request.user, group_id, user_id))
    try:
        group = Group.objects.get(id=group_id)

        # Check its a joinable group i.e. not corp or internal
        # And the user has permission to manage it
        if not GroupManager.joinable_group(group) or not GroupManager.can_manage_group(request.user, group):
            logger.warning("User %s attempted to remove a user from group %s but permission was denied" % (request.user,
                                                                                                           group_id))
            raise PermissionDenied

        try:
            user = group.user_set.get(id=user_id)
            # Remove group from user
            user.groups.remove(group)
            logger.info("User %s removed user %s from group %s" % (request.user, user, group))
            messages.success(request, "Removed user %s from group %s" % (user, group))
        except ObjectDoesNotExist:
            messages.warning(request, "User does not exist in that group")

    except ObjectDoesNotExist:
        messages.warning(request, "Group does not exist")

    return redirect('auth_group_membership_list', group_id)


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_accept_request(request, group_request_id):
    logger.debug("group_accept_request called by user %s for grouprequest id %s" % (request.user, group_request_id))
    try:
        group_request = GroupRequest.objects.get(id=group_request_id)
        group, created = Group.objects.get_or_create(name=group_request.group.name)

        if not GroupManager.joinable_group(group_request.group) or \
                not GroupManager.can_manage_group(request.user, group_request.group):
            raise PermissionDenied

        group_request.user.groups.add(group)
        group_request.user.save()
        group_request.delete()
        logger.info("User %s accepted group request from user %s to group %s" % (
            request.user, group_request.user, group_request.group.name))
        notify(group_request.user, "Group Application Accepted", level="success",
               message="Your application to %s has been accepted." % group_request.group)
        messages.success(request,
                         'Accepted application from %s to %s.' % (group_request.main_char, group_request.group))

    except PermissionDenied as p:
        logger.warning("User %s attempted to accept group join request %s but permission was denied" %
                       (request.user, group_request_id))
        raise p
    except:
        messages.error(request, 'An unhandled error occurred while processing the application from %s to %s.' % (
            group_request.main_char, group_request.group))
        logger.exception("Unhandled exception occurred while user %s attempting to accept grouprequest id %s." % (
            request.user, group_request_id))
        pass

    return redirect("auth_group_management")


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_reject_request(request, group_request_id):
    logger.debug("group_reject_request called by user %s for group request id %s" % (request.user, group_request_id))
    try:
        group_request = GroupRequest.objects.get(id=group_request_id)

        if not GroupManager.can_manage_group(request.user, group_request.group):
            raise PermissionDenied

        if group_request:
            logger.info("User %s rejected group request from user %s to group %s" % (
                request.user, group_request.user, group_request.group.name))
            group_request.delete()
            notify(group_request.user, "Group Application Rejected", level="danger",
                   message="Your application to %s has been rejected." % group_request.group)
            messages.success(request,
                             'Rejected application from %s to %s.' % (group_request.main_char, group_request.group))

    except PermissionDenied as p:
        logger.warning("User %s attempted to reject group join request %s but permission was denied" %
                       (request.user, group_request_id))
        raise p
    except:
        messages.error(request, 'An unhandled error occured while processing the application from %s to %s.' % (
            group_request.main_char, group_request.group))
        logger.exception("Unhandled exception occured while user %s attempting to reject group request id %s" % (
            request.user, group_request_id))
        pass

    return redirect("auth_group_management")


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_leave_accept_request(request, group_request_id):
    logger.debug(
        "group_leave_accept_request called by user %s for group request id %s" % (request.user, group_request_id))
    try:
        group_request = GroupRequest.objects.get(id=group_request_id)

        if not GroupManager.can_manage_group(request.user, group_request.group):
            raise PermissionDenied

        group, created = Group.objects.get_or_create(name=group_request.group.name)
        group_request.user.groups.remove(group)
        group_request.user.save()
        group_request.delete()
        logger.info("User %s accepted group leave request from user %s to group %s" % (
            request.user, group_request.user, group_request.group.name))
        notify(group_request.user, "Group Leave Request Accepted", level="success",
               message="Your request to leave %s has been accepted." % group_request.group)
        messages.success(request,
                         'Accepted application from %s to leave %s.' % (group_request.main_char, group_request.group))
    except PermissionDenied as p:
        logger.warning("User %s attempted to accept group leave request %s but permission was denied" %
                       (request.user, group_request_id))
        raise p
    except:
        messages.error(request, 'An unhandled error occured while processing the application from %s to leave %s.' % (
            group_request.main_char, group_request.group))
        logger.exception("Unhandled exception occured while user %s attempting to accept group leave request id %s" % (
            request.user, group_request_id))
        pass

    return redirect("auth_group_management")


@login_required
@user_passes_test(GroupManager.can_manage_groups)
def group_leave_reject_request(request, group_request_id):
    logger.debug(
        "group_leave_reject_request called by user %s for group request id %s" % (request.user, group_request_id))
    try:
        group_request = GroupRequest.objects.get(id=group_request_id)

        if not GroupManager.can_manage_group(request.user, group_request.group):
            raise PermissionDenied

        if group_request:
            group_request.delete()
            logger.info("User %s rejected group leave request from user %s for group %s" % (
                request.user, group_request.user, group_request.group.name))
            notify(group_request.user, "Group Leave Request Rejected", level="danger",
                   message="Your request to leave %s has been rejected." % group_request.group)
            messages.success(request, 'Rejected application from %s to leave %s.' % (
                group_request.main_char, group_request.group))
    except PermissionDenied as p:
        logger.warning("User %s attempted to reject group leave request %s but permission was denied" %
                       (request.user, group_request_id))
        raise p
    except:
        messages.error(request, 'An unhandled error occured while processing the application from %s to leave %s.' % (
            group_request.main_char, group_request.group))
        logger.exception("Unhandled exception occured while user %s attempting to reject group leave request id %s" % (
            request.user, group_request_id))
        pass

    return redirect("auth_group_management")


@login_required
def groups_view(request):
    logger.debug("groups_view called by user %s" % request.user)
    groups = []

    for group in GroupManager.get_joinable_groups():
        # Exclude hidden
        if not group.authgroup.hidden:
            group_request = GroupRequest.objects.filter(user=request.user).filter(group=group)

            groups.append({'group': group, 'request': group_request[0] if group_request else None})

    render_items = {'groups': groups}
    return render(request, 'registered/groups.html', context=render_items)


@login_required
def group_request_add(request, group_id):
    logger.debug("group_request_add called by user %s for group id %s" % (request.user, group_id))
    group = Group.objects.get(id=group_id)
    if not GroupManager.joinable_group(group):
        logger.warning("User %s attempted to join group id %s but it is not a joinable group" %
                       (request.user, group_id))
        messages.warning(request, "You cannot join that group")
        return redirect('auth_groups')
    if group.authgroup.open:
        logger.info("%s joining %s as is an open group" % (request.user, group))
        request.user.groups.add(group)
        return redirect("auth_groups")
    auth_info = AuthServicesInfo.objects.get(user=request.user)
    grouprequest = GroupRequest()
    grouprequest.status = _('Pending')
    grouprequest.group = group
    grouprequest.user = request.user
    grouprequest.main_char = EveManager.get_character_by_id(auth_info.main_char_id)
    grouprequest.leave_request = False
    grouprequest.save()
    logger.info("Created group request for user %s to group %s" % (request.user, Group.objects.get(id=group_id)))
    messages.success(request, 'Applied to group %s.' % group)
    return redirect("auth_groups")


@login_required
def group_request_leave(request, group_id):
    logger.debug("group_request_leave called by user %s for group id %s" % (request.user, group_id))
    group = Group.objects.get(id=group_id)
    if not GroupManager.joinable_group(group):
        logger.warning("User %s attempted to leave group id %s but it is not a joinable group" %
                       (request.user, group_id))
        messages.warning(request, "You cannot leave that group")
        return redirect('auth_groups')
    if group not in request.user.groups.all():
        logger.debug("User %s attempted to leave group id %s but they are not a member" %
                     (request.user, group_id))
        messages.warning(request, "You are not a member of that group")
        return redirect('auth_groups')
    if group.authgroup.open:
        logger.info("%s leaving %s as is an open group" % (request.user, group))
        request.user.groups.remove(group)
        return redirect("auth_groups")
    auth_info = AuthServicesInfo.objects.get(user=request.user)
    grouprequest = GroupRequest()
    grouprequest.status = _('Pending')
    grouprequest.group = group
    grouprequest.user = request.user
    grouprequest.main_char = EveManager.get_character_by_id(auth_info.main_char_id)
    grouprequest.leave_request = True
    grouprequest.save()
    logger.info("Created group leave request for user %s to group %s" % (request.user, Group.objects.get(id=group_id)))
    messages.success(request, 'Applied to leave group %s.' % group)
    return redirect("auth_groups")
