# -*- coding: utf-8 -*-
u"""
#########################################################
:mod:`wte.views.user` -- User functionality view handlers
#########################################################

The :mod:`~wte.views.user` module handles all user functionality.

Routes are defined in :func:`~wte.views.user.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import math
import formencode
import transaction
import uuid

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools.renderer import render
from sqlalchemy import and_, or_

from wte.decorators import (current_user, require_logged_in)
from wte.util import (unauthorised_redirect, State, send_email, get_config_setting,
                      paginate)
from wte.models import (DBSession, User, Permission, PermissionGroup)


def init(config):
    """Adds the user-specific routes (route name, URL pattern, handler):

    * ``users`` -- ``/users`` -- :func:`~wte.views.user.users`
    * ``users.action`` -- ``/users/action`` -- :func:`~wte.views.user.action`
    * ``user.login`` -- ``/users/login`` -- :func:`~wte.views.user.login`
    * ``user.logout`` -- ``/users/logout`` -- :func:`~wte.views.user.logout`
    * ``user.register`` -- ``/users/register`` --
      :func:`~wte.views.user.register`
    * ``user.forgotten_password`` -- ``/users/forgotten-password`` --
      :func:`~wte.views.user.forgotten_password`
    * ``user.view`` -- ``/users/{uid}`` -- :func:`~wte.views.user.view`
    * ``user.confirm`` -- ``/users/{uid}/confirm/{token}`` --
      :func:`~wte.views.user.confirm`
    * ``user.edit`` -- ``/users/{uid}/edit`` -- :func:`~wte.views.user.edit`
    * ``user.permissions`` -- ``/users/{uid}/permissions`` --
      :func:`~wte.views.user.permissions`
    * ``user.delete`` -- ``/users/{uid}/delete`` --
      :func:`~wte.views.user.delete`
    """
    config.add_route('users', '/users')
    config.add_route('users.action', '/users/action')
    config.add_route('user.login', '/users/login')
    config.add_route('user.logout', '/users/logout')
    config.add_route('user.register', '/users/register')
    config.add_route('user.forgotten_password', '/users/forgotten-password')
    config.add_route('user.view', '/users/{uid}')
    config.add_route('user.confirm', '/users/{uid}/confirm/{token}')
    config.add_route('user.edit', '/users/{uid}/edit')
    config.add_route('user.permissions', '/users/{uid}/permissions')
    config.add_route('user.delete', '/users/{uid}/delete')


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
    u"""Handles the ``/users`` URL, displaying all users if the current
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
                users = users.filter(User.validation_token == None)
            else:
                users = users.filter(User.validation_token != None)
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


class ActionSchema(formencode.Schema):
    u"""The :class:`~wte.views.user.ActionSchema` handles the validation of
    user action requests.
    """
    action = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf(['validate', 'password', 'delete']))
    u"""The action to apply"""
    confirm = formencode.validators.StringBool(if_empty=False, if_missing=False)
    u"""Whether the user has confirmed the action"""
    user_id = formencode.ForEach(formencode.validators.Int(), if_missing=None)
    q = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    u"""Optional query parameter for the redirect"""
    status = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    u"""Optional status parameter for the redirect"""
    start = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    u"""Optional start parameter for the redirect"""


@view_config(route_name='users.action')
@render({'text/html': 'users/action.html'})
@current_user()
def action(request):
    u"""Handles the ``/users/action`` URL, applying the given action to the
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
            params = ActionSchema().to_python(request.POST)
            if params['action'] != 'delete' or params['confirm']:
                with transaction.manager:
                    for user in dbsession.query(User).filter(User.id.in_(params['user_id'])):
                        if params['action'] == 'validate':
                            if user.validation_token is not None and user.allow('edit', request.current_user):
                                process_confirmation(request, user)
                        elif params['action'] == 'delete':
                            if user.allow('delete', request.current_user):
                                dbsession.delete(user)
                        elif params['action'] == 'password':
                            if user.validation_token is None and user.allow('edit', request.current_user):
                                user.random_password()
                request.session.flash('Your action has been applied to the selected users', queue='info')
                raise HTTPSeeOther(request.route_url('users', _query=query_params))
            else:
                return {'params': params,
                        'users': dbsession.query(User).filter(User.id.in_(params['user_id'])),
                        'query_params': query_params,
                        'crumbs': create_user_crumbs(request, [{'title': 'Confirm',
                                                                'url': request.current_route_url()}])}
        except formencode.Invalid:
            request.session.flash('Please select the action you wish to apply and the users to apply it to',
                                  queue='error')
            raise HTTPSeeOther(request.route_url('users', _query=query_params))
    else:
        unauthorised_redirect(request)


class PasswordValidator(formencode.FancyValidator):
    u"""The :class:`~wte.views.user.PasswordValidator` handles the checking of
    user-provided passwords against the database to allow / dissallow login.

    Login is disallowed, if the password does not match the e-mail address or
    if the :class:`~wte.models.User`'s ``validation_token`` is still set,
    meaning they have not confirmed their registration.

    Requires a SQLAlchemy database session to be available via
    ``state.dbsession``.
    """

    messages = {'nologin': 'No user exists with the given e-mail address or the password does not match',
                'noconfirmed': 'You must confirm your registration before being able to log in'}

    def _validate_python(self, value, state):
        user = state.dbsession.query(User).filter(User.email == value['email'].lower()).first()
        if user:
            if user.validation_token:
                raise formencode.api.Invalid(self.message('noconfirmed', state), value, state)
            elif not user.password_matches(value['password']):
                raise formencode.api.Invalid(self.message('nologin', state), value, state)
        else:
            raise formencode.api.Invalid(self.message('nologin', state), value, state)


class LoginSchema(formencode.Schema):
    u"""The :class:`~wte.views.user.LoginSchema` handles the validation of a
    login request.
    """
    return_to = formencode.validators.UnicodeString(if_missing=None)
    u"""URL to redirect to after a successful login (optional)"""
    email = formencode.validators.Email(not_empty=True)
    u"""E-mail address to log in with"""
    password = formencode.validators.UnicodeString(not_empty=True)
    u"""Password to log in with"""

    chained_validators = [PasswordValidator()]


@view_config(route_name='user.login')
@render({'text/html': 'users/login.html'})
@current_user()
def login(request):
    u"""Handles the "/users/login" URL, checking the submitted username and
    password against the stored :class:`~wte.models.User` and setting the
    necessary session variables if the login is successful.
    """
    if request.current_user.logged_in:
        request.session.flash('You are already logged in', queue='info')
        if 'return_to' in request.params:
            if request.params['return_to'] != request.route_url('root') and \
                    request.params['return_to'] != request.current_route_url():
                raise HTTPSeeOther(request.params['return_to'])
        raise HTTPSeeOther(request.route_url('user.modules', uid=request.current_user.id))
    if request.method == 'POST':
        try:
            dbsession = DBSession()
            params = LoginSchema().to_python(request.params, State(dbsession=dbsession))
            user = dbsession.query(User).filter(User.email == params['email'].lower()).first()
            request.current_user = user
            request.current_user.logged_in = True
            request.session['uid'] = user.id
            request.session.flash('Welcome, %s' % (user.display_name), queue='info')
            if 'return_to' in request.params:
                if request.params['return_to'] != request.route_url('root') and \
                        request.params['return_to'] != request.current_route_url():
                    raise HTTPSeeOther(request.params['return_to'])
            raise HTTPSeeOther(request.route_url('user.modules', uid=user.id))
        except formencode.api.Invalid as e:
            e.params = request.params
            return {'e': e}
    return {'crumbs': [{'title': 'Login', 'url': request.route_url('user.login'), 'current': True}]}


@view_config(route_name='user.logout')
@render({'text/html': 'users/logout.html'})
@current_user()
def logout(request):
    u"""Handles the "/users/logout" URL and deletes the current session,
    thus logging the user out
    """
    if request.method == 'POST':
        request.current_user.logged_in = False
        request.session.delete()
        raise HTTPSeeOther(request.route_url('root'))
    return {'crumbs': [{'title': 'Logout', 'url': request.route_url('user.logout'), 'current': True}]}


class UniqueEmailValidator(formencode.FancyValidator):
    u"""The :class:`~wte.views.user.UniqueEmailValidator` checks that the given
    e-mail address is not already used by a :class:`~wte.models.User`.

    Requires a SQLAlchemy database session to be available via
    ``state.dbsession``. If a ``state.userid`` is provided, then the
    :class:`~wte.models.User` with that `id` can have the same e-mail address.
    """
    messages = {'existing': 'A user with this e-mail address already exists'}

    def _validate_python(self, value, state):
        user = state.dbsession.query(User).filter(User.email == value).first()
        if user and (not hasattr(state, 'userid') or user.id != state.userid):
            raise formencode.Invalid(self.message('existing', state), value, state)


class EmailDomainValidator(formencode.FancyValidator):
    """The :class:`~wte.views.user.EmailDomainValidator` checks that the given
    e-mail address is in the list of allowed e-mail address domains.

    Requires that the list of allowed domains is available via the ``state.email_domains``
    attribute. If nothing is provided in the ``state``, then all e-mail addresses
    are seen as valid.
    """
    messages = {'wrongdomain': 'Only e-mail address in the following domains can be used: %(domains)s'}

    def _validate_python(self, value, state=None):
        if hasattr(state, 'email_domains') and state.email_domains:
            value = value[value.find('@') + 1:]
            if isinstance(state.email_domains, list):
                if value not in state.email_domains:
                    raise formencode.Invalid(self.message('wrongdomain',
                                                          state,
                                                          domains=', '.join(state.email_domains)),
                                             value,
                                             state)
            elif value != state.email_domains:
                raise formencode.Invalid(self.message('wrongdomain',
                                                      state,
                                                      domains=state.email_domains),
                                         value,
                                         state)


class RegisterSchema(formencode.Schema):
    u"""The :class:`~wte.user.views.RegisterSchema` handles the validation of
    registration requests.
    s"""
    return_to = formencode.validators.UnicodeString(if_missing=None)
    u"""URL to redirect to after a successful registration (optional)"""
    email = formencode.All(UniqueEmailValidator(),
                           EmailDomainValidator(),
                           formencode.validators.Email(not_empty=True))
    u"""E-mail address to register with"""
    email_confirm = formencode.validators.Email(not_empty=True)
    u"""Confirmation of the registration e-mail address"""
    name = formencode.validators.UnicodeString(not_empty=True)
    u"""Name of the registering user"""

    chained_validators = [formencode.validators.FieldsMatch('email',
                                                            'email_confirm')]


@view_config(route_name='user.register')
@render({'text/html': 'users/register.html'})
@current_user()
def register(request):
    u"""Handles the "/users/register" URL, displaying the registration form
    or if data is POSTed, creating a new user. Upon registration, a
    confirmation e-mail is sent to the given e-mail address.
    """
    if request.method == 'POST':
        try:
            dbsession = DBSession()
            params = RegisterSchema().to_python(request.params,
                                                State(dbsession=dbsession,
                                                      email_domains=get_config_setting(request,
                                                                                       key='registration.domains',
                                                                                       target_type='list',
                                                                                       default=None)))
            with transaction.manager:
                user = User(params['email'].lower(), params['name'])
                user.validation_token = uuid.uuid4().get_hex()
                dbsession.add(user)
            dbsession.add(user)
            send_email(request,
                       user.email,
                       get_config_setting(request, 'email.sender',
                                          default='no-reply@example.com'),
                       'Please confirm your registration',
                       '''Hello %s,

Thank you for registering with the Web Teaching Environment. To complete your
registration, please click on the following link or copy it into your browser:

%s

Best Regards,
Web Teaching Environment''' % (user.display_name,
                               request.route_url('user.confirm',
                                                 uid=user.id,
                                                 token=user.validation_token)))
            request.session.flash('''Your registration has been successful. A confirmation e-mail has been sent to
 the e-mail address you specified.''', queue='info')
            raise HTTPSeeOther(request.route_url('root'))
        except formencode.Invalid as e:
            e.params = request.params
            return {'e': e,
                    'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                               {'title': 'Register', 'url': request.route_url('user.register'), 'current': True}]}
    return {'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                       {'title': 'Register', 'url': request.route_url('user.register'), 'current': True}]}


def process_confirmation(request, user):
    u"""The :func:`~wte.views.user.process_confirmation` function handles
    clearing the ``validation_token``, generating a new password, and sending
    a welcome e-mail if the validation of the :class:`~wte.models.User` was
    successful.

    :param request: The request to use for configuration access
    :type request: :class:`~pyramid.request.Request`
    :param user: The user to process
    :type user: :class:`~wte.models.User`
    """
    user.validation_token = None
    new_password = user.random_password()
    send_email(request,
               user.email,
               get_config_setting(request, 'email.sender',
                                  default='no-reply@example.com'),
               'Log in to the Web Teaching Environment',
               '''Hello %s,

Thank you for confirming your registration with the Web Teaching Environment.
You can now log in using the following credentials:

Username: %s
Password: %s

Best Regards,
Web Teaching Environment''' % (user.display_name, user.email, new_password))


@view_config(route_name='user.confirm')
@render({'text/html': 'users/confirm.html'})
@current_user()
def confirm(request):
    u"""Handles the "/users/{uid}/confirm/{token}" URL, validating that the
    user with the given ``{uid}`` received the ``{token}`` at the given e-mail
    address.

    If confirmed, will send an e-mail with a new, random password.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(and_(User.id == request.matchdict['uid'],
                                             User.validation_token == request.matchdict['token'])).first()
    if user:
        status = u'success'
        with transaction.manager:
            dbsession.add(user)
            process_confirmation(request, user)
        dbsession.add(user)
    else:
        user = dbsession.query(User).filter(and_(User.id == request.matchdict['uid'],
                                                 User.validation_token is None)).first()
        if user:
            status = u'confirmed'
        else:
            status = u'fail'
    if request.current_user.has_permission('admin.users.view'):
        if status == u'fail':
            request.session.flash('Failed to validate the given user', queue='error')
        else:
            request.session.flash('The user has been validated and an e-mail with access details sent', queue='info')
        raise HTTPSeeOther(request.route_url('users'))
    else:
        return {'status': status,
                'crumbs': [{'title': 'Login', 'url': request.route_url('user.login')},
                           {'title': 'Register', 'url': request.route_url('user.register')},
                           {'title': 'Confirmation',
                            'url': request.route_url('user.confirm',
                                                     uid=request.matchdict['uid'],
                                                     token=request.matchdict['token']),
                            'current': True}]}


class ForgottenPasswordSchema(formencode.Schema):
    u"""The :class:`~wte.views.user.ForgottenPasswordSchema` handles the
    validation of forgotten password requests.
    """
    email = formencode.validators.Email(not_empty=True)
    u"""E-mail to request a new password or validation token for"""


def process_forgotten_password(request, user):
    u"""The :func:`~wte.views.user.process_forgotten_password` function handles
    generating a new password and sending the information e-mail. It can
    distinguish between :class:`~wte.models.User` who have been validated and
    those that have not yet and will send the appropriate e-mail.

    :param request: The request to use for URL generation
    :type request: :class:`~pyramid.request.Request`
    :param user: The user to generate a new password for
    :type user: :class:`~wte.models.User`
    """
    if user.validation_token:
        user.validation_token = uuid.uuid4().get_hex()
        send_email(request,
                   user.email,
                   get_config_setting(request, 'email.sender',
                                      default='no-reply@example.com'),
                   'Please confirm your registration',
                   '''Hello %s,

Thank you for registering with the Web Teaching Environment. To complete your
registration, please click on the following link or copy it into your browser:

%s

Best Regards,
Web Teaching Environment''' % (user.display_name, request.route_url('user.confirm',
                                                                    uid=user.id,
                                                                    token=user.validation_token)))
    else:
        new_password = user.random_password()
        send_email(request,
                   user.email,
                   get_config_setting(request, 'email.sender',
                                      default='no-reply@example.com'),
                   'Log in to the Web Teaching Environment',
                   '''Hello %s,

Thank you for confirming your registration with the Web Teaching Environment.
You can now log in using the following credentials:

Username: %s
Password: %s

Best Regards,
Web Teaching Environment''' % (user.display_name, user.email, new_password))


@view_config(route_name='user.forgotten_password')
@render({'text/html': 'users/forgotten_password.html'})
@current_user()
def forgotten_password(request):
    u"""Handles the "/users/forgotten-password" URL, showing the form where
    the user can provide their e-mail address. If the
    :class:`~wte.models.User` has a ``validation_token``, then an e-mail with a
    new validation token is sent, otherwise an e-mail with a new, random
    password is sent.
    """
    if request.method == 'POST':
        dbsession = DBSession()
        try:
            params = ForgottenPasswordSchema().to_python(request.params)
            user = dbsession.query(User).filter(User.email == params['email'].lower()).first()
            if user:
                with transaction.manager:
                    dbsession.add(user)
                    process_forgotten_password(request, user)
                dbsession.add(user)
                if user.validation_token is not None:
                    request.session.flash('A new confirmation e-mail has been sent to the' +
                                          ' specified e-mail address.', queue='info')
                else:
                    request.session.flash('A new password has been sent to the specified e-mail address.',
                                          queue='info')
                if request.current_user.has_permission('admin.users.view'):
                    raise HTTPSeeOther(request.route_url('users'))
                else:
                    raise HTTPSeeOther(request.route_url('root'))
            else:
                request.session.flash('A new password has been sent to the specified e-mail address.',
                                      queue='info')
            if request.current_user.has_permission('admin.users.view'):
                raise HTTPSeeOther(request.route_url('users'))
            else:
                raise HTTPSeeOther(request.route_url('root'))
        except formencode.api.Invalid as e:
            e.params = request.params
            return {'e': e}
    return {'crumbs': [{'title': 'Login',
                        'url': request.route_url('user.login')},
                       {'title': 'Forgotten Password',
                        'url': request.route_url('user.forgotten_password'), 'current': True}]}


@view_config(route_name='user.view')
@render({'text/html': 'users/view.html'})
@current_user()
@require_logged_in()
def view(request):
    u"""Handles the "/users/{uid}" URL, showing the user's profile.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
    if user:
        if user.allow('view', request.current_user):
            return {'user': user,
                    'crumbs': create_user_crumbs(request, [{'title': user.display_name,
                                                            'url': request.route_url('user.view', uid=user.id)}])}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class EditSchema(formencode.Schema):
    u"""The class:`~wte.views.user.EditSchema` handles the validation of
    changes to the :class:`~wte.models.User`.
    """
    email = formencode.All(UniqueEmailValidator(),
                           EmailDomainValidator(),
                           formencode.validators.Email(not_empty=True))
    u"""Updated e-mail address"""
    name = formencode.validators.UnicodeString(not_empty=True)
    u"""Updated name"""
    password = formencode.validators.UnicodeString()
    u"""Updated password"""


@view_config(route_name='user.edit')
@render({'text/html': 'users/edit.html'})
@current_user()
@require_logged_in()
def edit(request):
    u"""Handles the "/users/{uid}/edit" URL, providing the form and backend
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
                                                                                           default=None)))
                    with transaction.manager:
                        dbsession.add(user)
                        user.email = params['email']
                        user.display_name = params['name']
                        if params['password']:
                            user.new_password(params['password'])
                    request.session.flash('Profile updated', queue='info')
                    raise HTTPSeeOther(request.route_url('user.view', uid=request.matchdict['uid']))
                except formencode.api.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'user': user,
                            'crumbs': crumbs}
            return {'user': user,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='user.permissions')
@render({'text/html': 'users/permissions.html'})
@current_user()
@require_logged_in()
def permissions(request):
    u"""Handles the "/users/{uid}/permissions" URL, providing the form and
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
                request.session.flash('Permissions updated', queue='info')
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


@view_config(route_name='user.delete')
@render({'text/html': 'users/delete.html'})
@current_user()
@require_logged_in()
def delete(request):
    u"""Handles the "/users/{uid}/delete" URL, providing the form and backend
    functionality for deleting a :class:`~wte.models.User`. Also deletes all
    the data that is linked to that :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id == request.matchdict['uid']).first()
    if user:
        if user.allow('delete', request.current_user):
            if request.method == 'POST':
                with transaction.manager:
                    dbsession.delete(user)
                request.session.flash('The account has been deleted', queue='info')
                if request.current_user.has_permission('admin.users.view'):
                    raise HTTPSeeOther(request.route_url('users'))
                else:
                    raise HTTPSeeOther(request.route_url('root'))
            return {'user': user,
                    'crumbs': create_user_crumbs(request, [{'title': user.display_name,
                                                            'url': request.route_url('user.view', uid=user.id)},
                                                           {'title': 'Delete',
                                                            'url': request.route_url('user.delete', uid=user.id)}])}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
