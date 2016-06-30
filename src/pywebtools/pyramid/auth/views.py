# -*- coding: utf-8 -*-
"""
######################################################################
:mod:`pywebtools.pyramid.auth.views` -- Authentication Framework Views
######################################################################

Views that implement the backend for the authentication framework. The
:func:`~pywebtools.pyramid.auth.views.current_user` provides a decorator
that automatically adds the currently logged in user (or an anonymous
not-logged in user) into the current request.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from __future__ import (unicode_literals)  # Python 2.7 compatibility
from nine import str

import re
import transaction

from datetime import datetime, timedelta
from decorator import decorator
from formencode import Invalid, validators, All, ForEach
from pyramid.httpexceptions import HTTPSeeOther, HTTPOk, HTTPUnauthorized, HTTPNotFound
from sqlalchemy import and_, or_

from pywebtools.formencode import (CSRFSchema, State, UniqueEmailValidator, EmailDomainValidator,
                                   PasswordValidator)
from pywebtools.pyramid.util import request_from_args, get_config_setting, paginate
from pywebtools.pyramid.auth.decorators import current_user, require_logged_in
from pywebtools.pyramid.auth.models import User, TimeToken, Permission, PermissionGroup
from pywebtools.sqlalchemy import DBSession

# Post-action redirects
active_redirects = {}
# Post-action callbacks
active_callbacks = {}


# Pattern used for identifying replacable keyword arguments {argument-name}
KWARG_PATTERN = re.compile('\{([^}]*)\}')


def replace_kwargs(value, kwargs):
    """Replace any keyword arguments in ``value`` with the value specified
    in ``kwargs``. If the keyword argument does not exist in ``kwargs``,
    replace with an empty string.

    The function can handle both strings and dictionaries. In the case of
    dictionaries, both the keys and values are replaced.

    :params value: The value to replace
    :type value: ``str`` or ``dict``
    :param kwargs: The replacement values
    :type kwargs: ``dict``
    :return: The value with all keyword arguments replaced
    """
    if isinstance(value, dict):
        new_value = {}
        for key, dict_value in list(value.items()):
            new_value[replace_kwargs(key, kwargs)] = replace_kwargs(dict_value, kwargs)
        return new_value
    else:
        kwarg = re.match(KWARG_PATTERN, value)
        while kwarg:
            if kwarg.group(1) in kwargs:
                value = value.replace(kwarg.group(0), str(kwargs[kwarg.group(1)]))
            else:
                value = value.replace(kwarg.group(0), '')
            kwarg = re.match(KWARG_PATTERN, value)
        return value


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


def redirect(request, redirect_id, **kwargs):
    """Handles post-action redirects. If the redirection value is a string,
    uses that as the redirection route name. If it is a dictionary, then the
    value of the "route" key is used as the route name and the value of
    the "params" key is passed to the ``request.route_url`` function as keyword
    arguments. Uses :func:`~pywebtools.pyramid.auth.views.replace_kwargs` to
    allow dynamic data.

    :param request: The request to use for redirection
    :type request: :class:`~pyramid.request.Request`
    :param redirect_id: The identifier of the redirect to execute
    :type redirect_id: ``str``
    :param **kwargs: Keyword arguments to use for replacements
    """
    if redirect_id in active_redirects:
        redirect_route = active_redirects[redirect_id]
        if isinstance(redirect_route, dict):
            params = replace_kwargs(redirect_route['params'], kwargs)
            redirect_route = redirect_route['route']
        else:
            params = {}
        raise HTTPSeeOther(request.route_url(redirect_route, **params))
    elif '_default' in active_redirects:
        raise HTTPSeeOther(request.route_url(active_redirects['_default']))
    else:
        raise HTTPOk()


class LoginSchema(CSRFSchema):
    """The :class:`~pywebtools.pyramid.auth.views.LoginSchema` handles the validation of a
    login request.
    """
    return_to = validators.UnicodeString(if_missing=None)
    """URL to redirect to after a successful login (optional)"""
    email = validators.Email(not_empty=True)
    """E-mail address to log in with"""
    password = validators.UnicodeString(not_empty=True)
    """Password to log in with"""

    chained_validators = [PasswordValidator()]


@current_user()
def login(request):
    """Handles the "user.login" URL, checking the submitted username and
    password against the stored :class:`~pywebtools.pyramid.auth.models.User` and setting the
    necessary session variables if the login is successful.

    Uses either the ``return_to`` parameter in the request to redirect on success or
    the "user.login" redirection route, with parameter replacement "{uid}" will be replaced
    with the logged in user's identifier.
    """
    dbsession = DBSession()
    if request.current_user.logged_in:
        if 'return_to' in request.params and request.params['return_to'] != request.current_route_url():
            if '_default' in active_redirects and \
                    request.params['return_to'] != request.route_url(active_redirects['_default']):
                raise HTTPSeeOther(request.params['return_to'])
        redirect(request, 'user.login', uid=request.current_user.id)
    if request.method == 'POST':
        try:
            dbsession = DBSession()
            params = LoginSchema().to_python(request.params, State(dbsession=dbsession,
                                                                   request=request,
                                                                   user_class=User))
            user = dbsession.query(User).filter(User.email == params['email'].lower()).first()
            request.current_user = user
            request.current_user.logged_in = True
            request.session['uid'] = user.id
            request.session.new_csrf_token()
            if 'return_to' in request.params and request.params['return_to'] != request.current_route_url():
                if '_default' in active_redirects and \
                        request.params['return_to'] != request.route_url(active_redirects['_default']):
                    raise HTTPSeeOther(request.params['return_to'])
            redirect(request, 'user.login', uid=request.current_user.id)
        except Invalid as e:
            return {'errors': e.error_dict if e.error_dict else {'email': e.msg,
                                                                 'password': e.msg},
                    'values': request.params,
                    'crumbs': [{'title': 'Login', 'url': request.route_url('user.login'), 'current': True}]}
    return {'crumbs': [{'title': 'Login', 'url': request.route_url('user.login'), 'current': True}]}


@current_user()
def logout(request):
    """Handles the "user.logout" URL and deletes the current session,
    thus logging the user out.

    Redirects to the "user.logout" redirection route.
    """
    if request.method == 'POST':
        try:
            CSRFSchema().to_python(request.params, State(request=request))
            request.current_user.logged_in = False
            request.session.delete()
            redirect(request, 'user.logout')
        except Invalid as e:
            return {'errors': e.error_dict,
                    'crumbs': [{'title': 'Logout', 'url': request.route_url('user.logout'), 'current': True}]}
    return {'crumbs': [{'title': 'Logout', 'url': request.route_url('user.logout'), 'current': True}]}


class RegisterSchema(CSRFSchema):
    """The :class:`~pywebtools.pyramid.auth.RegisterSchema` handles the validation of
    registration requests.
    s"""
    return_to = validators.UnicodeString(if_missing=None)
    """URL to redirect to after a successful registration (optional)"""
    email = All(UniqueEmailValidator(),
                EmailDomainValidator(),
                validators.Email(not_empty=True))
    """E-mail address to register with"""
    email_confirm = validators.Email(not_empty=True)
    """Confirmation of the registration e-mail address"""
    name = validators.UnicodeString(not_empty=True)
    """Name of the registering user"""

    chained_validators = [validators.FieldsMatch('email',
                                                 'email_confirm')]


@current_user()
def register(request):
    """Handles the "user.register" URL, displaying the registration form
    or if data is POSTed, creating a new user.

    On a successful registration, calls the "user.created" callback with
    three parameters: the current request object, the new :class:`~pywebtools.pyramid.auth.models.User`,
    and the validation :class:`~pywebtools.pyramid.auth.models.TimeToken`.

    On a successful registration, redirects to the "user.register" redirection route.
    """
    if request.method == 'POST':
        try:
            dbsession = DBSession()
            params = RegisterSchema().to_python(request.params,
                                                State(dbsession=dbsession,
                                                      email_domains=get_config_setting(request,
                                                                                       key='registration.domains',
                                                                                       target_type='list',
                                                                                       default=None),
                                                      user_class=User,
                                                      request=request))
            with transaction.manager:
                user = User(email=params['email'].lower(),
                            display_name=params['name'],
                            status='unconfirmed')
                dbsession.add(user)
            with transaction.manager:
                dbsession.add(user)
                token = TimeToken(user.id,
                                  'validate_account',
                                  datetime.now() + timedelta(seconds=3600))
                dbsession.add(token)
            dbsession.add(user)
            dbsession.add(token)
            if 'user.created' in active_callbacks:
                active_callbacks['user.created'](request, user, token)
            redirect(request, 'user.register')
        except Invalid as e:
            return {'errors': e.error_dict,
                    'values': request.params,
                    'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                               {'title': 'Register', 'url': request.route_url('user.register'), 'current': True}]}
    return {'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                       {'title': 'Register', 'url': request.route_url('user.register'), 'current': True}]}


@current_user()
def confirm(request):
    """Handles the "users.confirm" URL, validating that the
    user with the ``{token}`` has access to the e-mail address they provided.

    On a successful confirmation, calls the "user.validated" callback with
    three parameters: the current request object, the new :class:`~pywebtools.pyramid.auth.models.User`,
    and the validation :class:`~pywebtools.pyramid.auth.models.TimeToken`.

    If overriding the URL, the URL must only have a ``{token}`` parameter.
    """
    dbsession = DBSession()
    token = dbsession.query(TimeToken).filter(and_(TimeToken.action == 'validate_account',
                                                   TimeToken.token == request.matchdict['token'],
                                                   TimeToken.timeout >= datetime.now())).first()
    if token:
        user = token.user
        with transaction.manager:
            dbsession.delete(token)
            dbsession.add(user)
            user.status = 'active'
            token = TimeToken(user.id,
                              'reset_password',
                              datetime.now() + timedelta(seconds=1200))
            dbsession.add(token)
        dbsession.add(user)
        dbsession.add(token)
        if 'user.validated' in active_callbacks:
            active_callbacks['user.validated'](request, user, token)
        return {'status': 'success',
                'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                           {'title': 'Register', 'url': request.route_url('user.register')},
                           {'title': 'Confirmation',
                            'url': request.route_url('user.confirm',
                                                     token=request.matchdict['token'])}]}
    else:
        return {'status': 'fail',
                'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                           {'title': 'Register', 'url': request.route_url('user.register')},
                           {'title': 'Confirmation',
                            'url': request.route_url('user.confirm',
                                                     token=request.matchdict['token'])}]}


class ForgottenPasswordSchema(CSRFSchema):
    """The :class:`~pywebtools.pyramid.auth.views.ForgottenPasswordSchema` handles the
    validation of forgotten password requests.
    """
    return_to = validators.UnicodeString(if_missing=None)
    """URL to redirect to after a successful password request"""
    email = validators.Email(not_empty=True)
    """E-mail to request a new password or validation token for"""


@current_user()
def forgotten_password(request):
    """Handles the "user.forgotten_password" URL, showing the form where
    the user can provide their e-mail address.

    If the e-mail address provided does not match any known e-mail address,
    calls the "user.password_reset_failed" callback with the current request.
    If the e-mail address is known and the :class:`~pywebtools.pyramid.auth.models.User`
    status is "unconfirmed", calls the "user.created" callback with the current request,
    the :class:`~pywebtools.pyramid.auth.models.User`, and a new
    :class:`~pywebtools.pyramid.auth.models.TimeToken`. If the :class:`~pywebtools.pyramid.auth.models.User`
    status is "active", calls the "user.password_reset" callback with the current request,
    the :class:`~pywebtools.pyramid.auth.models.User`, and a new
    :class:`~pywebtools.pyramid.auth.models.TimeToken`.

    Uses either the ``return_to`` parameter in the request to redirect on success or
    the "user.forgotten_password" redirection route.
    """
    if request.method == 'POST':
        dbsession = DBSession()
        try:
            params = ForgottenPasswordSchema().to_python(request.params,
                                                         State(request=request))
            user = dbsession.query(User).filter(User.email == params['email'].lower()).first()
            if user:
                with transaction.manager:
                    dbsession.add(user)
                    if user.status == 'unconfirmed':
                        token = TimeToken(user.id,
                                          'validate_account',
                                          datetime.now() + timedelta(seconds=3600))
                        dbsession.add(token)
                    else:
                        token = TimeToken(user.id,
                                          'reset_password',
                                          datetime.now() + timedelta(seconds=1200))
                        dbsession.add(token)
                dbsession.add(user)
                dbsession.add(token)
                if user.status == 'unconfirmed':
                    if 'user.created' in active_callbacks:
                        active_callbacks['user.created'](request, user, token)
                else:
                    if 'user.password_reset' in active_callbacks:
                        active_callbacks['user.password_reset'](request, user, token)
            else:
                if 'user.password_reset_failed' in active_callbacks:
                    active_callbacks['user.password_reset_failed'](request)
            if 'return_to' in request.params and request.params['return_to'] != request.current_route_url():
                if '_default' in active_redirects and \
                        request.params['return_to'] != request.route_url(active_redirects['_default']):
                    raise HTTPSeeOther(request.params['return_to'])
            redirect(request, 'user.forgotten_password')
        except Invalid as e:
            return {'errors': e.error_dict,
                    'values': request.params,
                    'crumbs': [{'title': 'Login',
                                'url': request.route_url('user.login')},
                               {'title': 'Forgotten Password',
                                'url': request.route_url('user.forgotten_password'), 'current': True}]}
    return {'crumbs': [{'title': 'Login',
                        'url': request.route_url('user.login')},
                       {'title': 'Forgotten Password',
                        'url': request.route_url('user.forgotten_password'), 'current': True}]}


class ResetPasswordSchema(CSRFSchema):
    """The :class:`~pywebtools.pyramid.auth.ResetPasswordSchema` handles the validation of
    password reset requests."""
    password = validators.UnicodeString(not_empty=True)
    """New password"""
    password_confirm = validators.UnicodeString(not_empty=True)
    """Updated password"""

    chained_validators = [validators.FieldsMatch('password', 'password_confirm')]


@current_user()
def reset_password(request):
    """Handles the "user.forgotten_password" URL, showing the form where
    the user can provide their e-mail address.

    If token is valid, calls the "user.password_reset_complete" callback with the
    current request and the :class:`~pywebtools.pyramid.auth.models.User`.

    Uses either the ``return_to`` parameter in the request to redirect on success or
    the "user.login" redirection route, with parameter replacement "{uid}" will be replaced
    with the logged in user's identifier.

    If overriding the URL, the URL must only have a ``{token}`` parameter.
    """
    dbsession = DBSession()
    token = dbsession.query(TimeToken).filter(and_(TimeToken.action == 'reset_password',
                                                   TimeToken.token == request.matchdict['token'],
                                                   TimeToken.timeout >= datetime.now())).first()
    if token:
        if request.method == 'POST':
            try:
                params = ResetPasswordSchema().to_python(request.params,
                                                         State(request=request))
                user = token.user
                with transaction.manager:
                    dbsession.add(user)
                    user.new_password(params['password'])
                    user.login_limit = 0
                    dbsession.delete(token)
                dbsession.add(user)
                request.current_user = user
                request.current_user.logged_in = True
                request.session['uid'] = user.id
                request.session.new_csrf_token()
                if 'user.password_reset_complete' in active_callbacks:
                    active_callbacks['user.password_reset_complete'](request, user)
                redirect(request, 'user.reset_password', uid=request.current_user.id)
            except Invalid as e:
                return {'errors': e.error_dict,
                        'values': request.params,
                        'allow_reset': True,
                        'crumbs': [{'title': 'Login',
                                    'url': request.route_url('user.login')},
                                   {'title': 'Reset Password',
                                    'url': request.route_url('user.reset_password',
                                                             token=request.matchdict['token']), 'current': True}]}
        else:
            return {'allow_reset': True,
                    'crumbs': [{'title': 'Login',
                                'url': request.route_url('user.login')},
                               {'title': 'Reset Password',
                                'url': request.route_url('user.reset_password',
                                                         token=request.matchdict['token']), 'current': True}]}
    else:
        return {'allow_reset': False,
                'crumbs': [{'title': 'Login',
                            'url': request.route_url('user.login')},
                           {'title': 'Reset Password',
                            'url': request.route_url('user.reset_password',
                                                     token=request.matchdict['token']), 'current': True}]}




@current_user()
def users(request):
    """Handles the ``/users`` URL, displaying all users if the current
    :class:`~pywebtools.pyramid.auth.models.User` has the "admin.users.view"
    :class:`~pywebtools.pyramid.auth.models.Permission`.
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
    action = All(validators.UnicodeString(not_empty=True),
                 validators.OneOf(['validate', 'password', 'delete']))
    """The action to apply"""
    confirm = validators.StringBool(if_empty=False, if_missing=False)
    """Whether the user has confirmed the action"""
    user_id = ForEach(validators.Int(), if_missing=None)
    """User ids to apply the action to"""
    q = validators.UnicodeString(if_empty=None, if_missing=None)
    """Optional query parameter for the redirect"""
    status = validators.UnicodeString(if_empty=None, if_missing=None)
    """Optional status parameter for the redirect"""
    start = validators.UnicodeString(if_empty=None, if_missing=None)
    """Optional start parameter for the redirect"""


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
        except Invalid as e:
            print(e)
            request.session.flash('Please select the action you wish to apply and the users to apply it to',
                                  queue='error')
            raise HTTPSeeOther(request.route_url('users', _query=query_params))
    else:
        unauthorised_redirect(request)


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
    email = All(UniqueEmailValidator(),
                EmailDomainValidator(),
                validators.Email(not_empty=True))
    """Updated e-mail address"""
    name = validators.UnicodeString(not_empty=True)
    """Updated name"""
    password = validators.UnicodeString()
    """Updated password"""


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
                                                          user_class=User,
                                                          request=request))
                    with transaction.manager:
                        dbsession.add(user)
                        user.email = params['email']
                        user.display_name = params['name']
                        if params['password']:
                            user.new_password(params['password'])
                    raise HTTPSeeOther(request.route_url('user.view', uid=request.matchdict['uid']))
                except Invalid as e:
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
                except Invalid as e:
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
                except Invalid as e:
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
