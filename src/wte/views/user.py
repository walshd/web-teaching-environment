# -*- coding: utf-8 -*-
"""
#########################################################
:mod:`wte.views.user` -- User functionality view handlers
#########################################################

The :mod:`~wte.views.user` module handles all user functionality.

Routes are defined in :func:`~wte.views.user.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import formencode
import transaction

from datetime import datetime, timedelta
from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools.formencode import State, CSRFSchema, UniqueEmailValidator, EmailDomainValidator
from pywebtools.pyramid import auth as pyramid_auth
from pywebtools.pyramid.auth import current_user
from pywebtools.pyramid.auth.models import (User, Permission, PermissionGroup, TimeToken)
from pywebtools.sqlalchemy import DBSession
from sqlalchemy import or_

from wte.decorators import (require_logged_in)
from wte.util import (unauthorised_redirect, send_email, get_config_setting,
                      paginate)


def init(config):
    """Adds the user-specific routes (route name, URL pattern, handler):

    * ``users`` -- ``/users`` -- :func:`~wte.views.user.users`
    * ``users.action`` -- ``/users/action`` -- :func:`~wte.views.user.action`
    * ``user.view`` -- ``/users/{uid}`` -- :func:`~wte.views.user.view`
    * ``user.edit`` -- ``/users/{uid}/edit`` -- :func:`~wte.views.user.edit`
    * ``user.permissions`` -- ``/users/{uid}/permissions`` --
      :func:`~wte.views.user.permissions`
    * ``user.delete`` -- ``/users/{uid}/delete`` --
      :func:`~wte.views.user.delete`

    Also initialises the :mod:`pywebtools.pyramid.auth` authentication system
    """
    pyramid_auth.init(config,
                      renderers={'user.login': 'wte:templates/users/login.kajiki',
                                 'user.logout': 'wte:templates/users/logout.kajiki',
                                 'user.register': 'wte:templates/users/register.kajiki',
                                 'user.confirm': 'wte:templates/users/confirm.kajiki',
                                 'user.forgotten_password': 'wte:templates/users/forgotten_password.kajiki',
                                 'user.reset_password': 'wte:templates/users/reset_password.kajiki'},
                      redirects={'_default': 'root',
                                 'user.login': {'route': 'part.list',
                                                'params': {'_query': {'user_id': '{uid}'}}},
                                 'user.logout': 'root',
                                 'user.register': 'root',
                                 'user.forgotten_password': 'root',
                                 'user.reset_password': {'route': 'part.list',
                                                         'params': {'_query': {'user_id': '{uid}'}}}},
                      callbacks={'user.created': new_user_created,
                                 'user.validated': new_user_validated,
                                 'user.password_reset': password_reset,
                                 'user.password_reset_failed': password_reset_failed,
                                 'user.password_reset_complete': password_reset_complete})
    config.add_route('users', '/users')
    config.add_route('users.action', '/users/action')
    config.add_route('user.view', '/users/{uid}')
    config.add_route('user.edit', '/users/{uid}/edit')
    config.add_route('user.permissions', '/users/{uid}/permissions')
    config.add_route('user.delete', '/users/{uid}/delete')


def new_user_created(request, user, token):
    """Callback that sends an e-mail to the newly created user's e-mail address
    to give them a validation link.

    :param request: The request to use for configuration settings
    :type request: :class:`~pyramid.request.Request`
    :param user: The user to send the e-mail to
    :type user: :class:`~pywebtools.pyramid.auth.models.User`
    :param token: The validation token
    :type token: :class:`~pywebtools.pyramid.auth.models.TimeToken`
    """
    request.session.flash('A confirmation e-mail has been sent to the e-mail address you provided.', queue='info')
    send_email(request,
               user.email,
               get_config_setting(request, 'email.sender',
                                  default='no-reply@example.com'),
               'Please confirm your registration',
               '''Hello %s,

Thank you for registering with the Web Teaching Environment. To complete your
registration, please click on the following link or copy it into your browser:

%s

This link is valid for 60 minutes. If you do not confirm your registration within
that time, you will need to use the "Forgotten Password" function to request a new
confirmation link.

Best Regards,
Web Teaching Environment''' % (user.display_name,
                               request.route_url('user.confirm',
                                                 token=token.token)))


def new_user_validated(request, user, token):
    """Callback that sends an e-mail to the newly created user's e-mail address
    to give them a password-reset link.

    :param request: The request to use for configuration settings
    :type request: :class:`~pyramid.request.Request`
    :param user: The user to send the e-mail to
    :type user: :class:`~pywebtools.pyramid.auth.models.User`
    :param token: The validation token
    :type token: :class:`~pywebtools.pyramid.auth.models.TimeToken`
    """
    send_email(request,
               user.email,
               get_config_setting(request, 'email.sender',
                                  default='no-reply@example.com'),
               'Registration for the Web Teaching Environment Complete',
               '''Hello %s,

Thank you for completing the registration process. To log in, please
click on the following link and set a new password:

%s

The link is valid for 20 minutes. If you do not set a password within that time,
you will need to use the "Forgotten Password" function to request a new confirmation
link.

Best Regards,
Web Teaching Environment''' % (user.display_name, request.route_url('user.reset_password', token=token.token)))


def password_reset(request, user, token):
    """Callback that sends an e-mail to the user's e-mail address with a
    link to reset their password.

    :param request: The request to use for configuration settings
    :type request: :class:`~pyramid.request.Request`
    :param user: The user to send the e-mail to
    :type user: :class:`~pywebtools.pyramid.auth.models.User`
    """
    request.session.flash('A password reset link has been sent to the e-mail address you provided.', queue='info')
    send_email(request,
               user.email,
               get_config_setting(request, 'email.sender',
                                  default='no-reply@example.com'),
               'Password for the Web Teaching Environment reset',
               '''Hello %s,

You have asked to have your password reset. To complete the reset password
click on the following link or copy it into your browser:

%s

The link is valid for 20 minutes. If you do not set a password within that time,
you will need to use the "Forgotten Password" function to request a new confirmation
link.

If you did not ask for your password to be reset, then please check that
nobody else has access to your e-mail account and might be trying to
access your Web Teaching Environment account.

Best Regards,
Web Teaching Environment''' % (user.display_name, request.route_url('user.reset_password', token=token.token)))


def password_reset_failed(request):
    """Callback that handles a failed password reset."""
    request.session.flash('A password reset link has been sent to the e-mail address you provided.', queue='info')


def password_reset_complete(request, user):
    """Callback that sends an e-mail to the user's e-mail address letting them
    know that their password has been reset.

    :param request: The request to use for configuration settings
    :type request: :class:`~pyramid.request.Request`
    :param user: The user to send the e-mail to
    :type user: :class:`~pywebtools.pyramid.auth.models.User`
    """
    send_email(request,
               user.email,
               get_config_setting(request, 'email.sender',
                                  default='no-reply@example.com'),
               'Reset your password for the Web Teaching Environment',
               '''Hello %s,

You have just reset your password for the Web Teaching Environment.

If you have not done so, then please contact your administrator as soon as
possible as somebody else may have gained access to your account.

Best Regards,
Web Teaching Environment''' % user.display_name)


def create_user_crumbs(request, crumbs):
    """Creates the base-list of breadcrumbs, depending on the current
    users authorisation level.
    """
    if request.current_user.has_permission('admin.users.view'):
        crumbs.insert(0, {'title': 'Users',
                          'url': request.route_url('users')})
    if request.current_user.has_permission('admin'):
        crumbs.insert(0, {'title': 'Administration',
                          'url': request.route_url('admin')})
    crumbs[-1]['current'] = True
    return crumbs


@view_config(route_name='users', renderer='wte:templates/users/list.kajiki')
@current_user()
def users(request):
    """Handles the ``/users`` URL, displaying all users if the current
    :class:`~wte.models.User` has the "admin.users.view"
    :class:`~wte.models.Permission`.
    """
    if request.current_user.has_permission('admin.users.view'):
        dbsession = DBSession()
        users = dbsession.query(User)
        query_params = []
        if 'q' in request.params and request.params['q']:
            users = users.filter(or_(User.display_name.contains(request.params['q']),
                                     User.email.contains(request.params['q'])))
            query_params.append(('q', request.params['q']))
        if 'status' in request.params and request.params['status']:
            query_params.append(('status', request.params['status']))
            if request.params['status'] == 'confirmed':
                users = users.filter(User.status == 'active')
            else:
                users = users.filter(User.status != 'active')
        start = 0
        if 'start' in request.params:
            try:
                start = int(request.params['start'])
            except ValueError:
                pass
        users = users.order_by(User.display_name)
        users = users.offset(start).limit(30)
        pages = paginate(request, users, start, 30, query_params=query_params)
        return {'users': users,
                'pages': pages,
                'crumbs': create_user_crumbs(request, [])}
    else:
        unauthorised_redirect(request)


class ActionSchema(CSRFSchema):
    """The :class:`~wte.views.user.ActionSchema` handles the validation of
    user action requests.
    """
    action = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf(['validate', 'password', 'delete']))
    """The action to apply"""
    confirm = formencode.validators.StringBool(if_empty=False, if_missing=False)
    """Whether the user has confirmed the action"""
    user_id = formencode.ForEach(formencode.validators.Int(), if_missing=None)
    """User ids to apply the action to"""
    q = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """Optional query parameter for the redirect"""
    status = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """Optional status parameter for the redirect"""
    start = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """Optional start parameter for the redirect"""


@view_config(route_name='users.action', renderer='wte:templates/users/action.kajiki')
@current_user()
def action(request):
    """Handles the ``/users/action`` URL, applying the given action to the
    list of selected users. Requires that the current
    :class:`~wte.models.User` has the "admin.users.view"
    :class:`~wte.models.Permission`.
    """
    if request.current_user.has_permission('admin.users.view'):
        dbsession = DBSession()
        try:
            query_params = []
            for param in ['q', 'status', 'start']:
                if param in request.params and request.params[param]:
                    query_params.append((param, request.params[param]))
            params = ActionSchema().to_python(request.params,
                                              State(request=request))
            if params['action'] != 'delete' or params['confirm']:
                with transaction.manager:
                    for user in dbsession.query(User).filter(User.id.in_(params['user_id'])):
                        if params['action'] == 'validate':
                            if user.status == 'unconfirmed' and user.allow('edit', request.current_user):
                                user.status = 'active'
                        elif params['action'] == 'delete':
                            if user.allow('delete', request.current_user):
                                dbsession.delete(user)
                        elif params['action'] == 'password':
                            if user.status == 'active' and user.allow('edit', request.current_user):
                                token = TimeToken(user.id,
                                                  'reset_password',
                                                  datetime.now() + timedelta(seconds=1200))
                                dbsession.add(token)
                                dbsession.flush()
                                password_reset(request, user, token)
                raise HTTPSeeOther(request.route_url('users', _query=query_params))
            else:
                return {'params': params,
                        'users': dbsession.query(User).filter(User.id.in_(params['user_id'])),
                        'query_params': query_params,
                        'crumbs': create_user_crumbs(request, [{'title': 'Confirm',
                                                                'url': request.current_route_url()}])}
        except formencode.Invalid as e:
            print(e)
            request.session.flash('Please select the action you wish to apply and the users to apply it to',
                                  queue='error')
            raise HTTPSeeOther(request.route_url('users', _query=query_params))
    else:
        unauthorised_redirect(request)


@view_config(route_name='user.view', renderer='wte:templates/users/view.kajiki')
@current_user()
@require_logged_in()
def view(request):
    """Handles the "/users/{uid}" URL, showing the user's profile.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
    if user:
        if user.allow('view', request.current_user):
            return {'user': user,
                    'crumbs': create_user_crumbs(request, [{'title': user.display_name,
                                                            'url': request.route_url('user.view', uid=user.id)}]),
                    'help': ['user', 'user', 'profile.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class EditSchema(CSRFSchema):
    """The class:`~wte.views.user.EditSchema` handles the validation of
    changes to the :class:`~wte.models.User`.
    """
    email = formencode.All(UniqueEmailValidator(),
                           EmailDomainValidator(),
                           formencode.validators.Email(not_empty=True))
    """Updated e-mail address"""
    name = formencode.validators.UnicodeString(not_empty=True)
    """Updated name"""
    password = formencode.validators.UnicodeString()
    """Updated password"""


@view_config(route_name='user.edit', renderer='wte:templates/users/edit.kajiki')
@current_user()
@require_logged_in()
def edit(request):
    """Handles the "/users/{uid}/edit" URL, providing the form and backend
    functionality to update the user's profile.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
    if user:
        if user.allow('edit', request.current_user):
            crumbs = create_user_crumbs(request, [{'title': user.display_name,
                                                   'url': request.route_url('user.view', uid=user.id)},
                                                  {'title': 'Edit',
                                                   'url': request.route_url('user.edit', uid=user.id)}])
            if request.method == 'POST':
                try:
                    params = EditSchema().to_python(request.params,
                                                    State(dbsession=dbsession,
                                                          userid=user.id,
                                                          email_domains=get_config_setting(request,
                                                                                           key='registration.domains',
                                                                                           target_type='list',
                                                                                           default=None),
                                                          user_class=User))
                    with transaction.manager:
                        dbsession.add(user)
                        user.email = params['email']
                        user.display_name = params['name']
                        if params['password']:
                            user.new_password(params['password'])
                    raise HTTPSeeOther(request.route_url('user.view', uid=request.matchdict['uid']))
                except formencode.api.Invalid as e:
                    return {'e': e.error_dict,
                            'values': request.params,
                            'user': user,
                            'crumbs': crumbs,
                            'help': ['user', 'user', 'profile.html']}
            return {'user': user,
                    'crumbs': crumbs,
                    'help': ['user', 'user', 'profile.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='user.permissions', renderer='wte:templates/users/permissions.kajiki')
@current_user()
@require_logged_in()
def permissions(request):
    """Handles the "/users/{uid}/permissions" URL, providing the form and
    backend functionality for setting the :class:`~wte.models.Permission` and
    :class:`~wte.models.PermissionGroup` that the :class:`~wte.models.User`
    belongs to.
    """
    if request.current_user.has_permission('admin.users.permissions'):
        dbsession = DBSession()
        user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
        if user:
            permission_groups = dbsession.query(PermissionGroup).order_by(PermissionGroup.title)
            permissions = dbsession.query(Permission).order_by(Permission.title)
            if request.method == 'POST':
                try:
                    CSRFSchema(allow_extra_fields=True).to_python(request.params, State(request=request))
                    with transaction.manager:
                        dbsession.add(user)
                        ids = request.params.getall('permission_group')
                        if ids:
                            user.permission_groups = dbsession.query(PermissionGroup).\
                                filter(PermissionGroup.id.in_(ids)).all()
                        else:
                            user.permission_groups = []
                        ids = request.params.getall('permission')
                        if ids:
                            user.permissions = dbsession.query(Permission).filter(Permission.id.in_(ids)).all()
                        else:
                            user.permissions = []
                    dbsession.add(user)
                    dbsession.add(request.current_user)
                    if request.current_user.has_permission('admin.users.view'):
                        raise HTTPSeeOther(request.route_url('users'))
                    else:
                        raise HTTPSeeOther(request.route_url('users.view', uid=user.id))
                except formencode.Invalid as e:
                    print(e)
                    return {'errors': e.error_dict,
                            'user': user,
                            'permission_groups': permission_groups,
                            'permissions': permissions,
                            'crumbs': create_user_crumbs(request, [{'title': user.display_name,
                                                                    'url': request.route_url('user.view',
                                                                                             uid=user.id)},
                                                                   {'title': 'Permissions',
                                                                    'url': request.route_url('user.permissions',
                                                                                             uid=user.id)}])}
            return {'user': user,
                    'permission_groups': permission_groups,
                    'permissions': permissions,
                    'crumbs': create_user_crumbs(request, [{'title': user.display_name,
                                                            'url': request.route_url('user.view',
                                                                                     uid=user.id)},
                                                           {'title': 'Permissions',
                                                            'url': request.route_url('user.permissions',
                                                                                     uid=user.id)}])}
        else:
            raise HTTPNotFound()
    else:
        unauthorised_redirect(request)


@view_config(route_name='user.delete', renderer='wte:templates/users/delete.kajiki')
@current_user()
@require_logged_in()
def delete(request):
    """Handles the "/users/{uid}/delete" URL, providing the form and backend
    functionality for deleting a :class:`~wte.models.User`. Also deletes all
    the data that is linked to that :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
    if user:
        if user.allow('delete', request.current_user):
            if request.method == 'POST':
                try:
                    CSRFSchema().to_python(request.params, State(request=request))
                    with transaction.manager:
                        dbsession.delete(user)
                    request.session.flash('The account has been deleted', queue='info')
                    if request.current_user.has_permission('admin.users.view'):
                        raise HTTPSeeOther(request.route_url('users'))
                    else:
                        raise HTTPSeeOther(request.route_url('root'))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'user': user,
                            'crumbs': create_user_crumbs(request,
                                                         [{'title': user.display_name,
                                                           'url': request.route_url('user.view', uid=user.id)},
                                                          {'title': 'Delete',
                                                           'url': request.route_url('user.delete', uid=user.id)}])}
            return {'user': user,
                    'crumbs': create_user_crumbs(request, [{'title': user.display_name,
                                                            'url': request.route_url('user.view', uid=user.id)},
                                                           {'title': 'Delete',
                                                            'url': request.route_url('user.delete', uid=user.id)}])}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
