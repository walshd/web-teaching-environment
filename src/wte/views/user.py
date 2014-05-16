# -*- coding: utf-8 -*-
'''
Created on 12 May 2014

@author: mhall
'''
import transaction
import formencode
import uuid

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised
from sqlalchemy import and_

from wte.decorators import current_user
from wte.util import (unauthorised_redirect, State, send_email, get_config_setting)
from wte.models import (DBSession, User, Permission, PermissionGroup)

def init(config):
    """Adds the user-specific routes.
    """
    config.add_route('users', '/users')
    config.add_route('user.login', '/users/login')
    config.add_route('user.logout', '/users/logout')
    config.add_route('user.register', '/users/register')
    config.add_route('user.forgotten_password', '/users/forgotten-password')
    config.add_route('user.view', '/users/{uid}')
    config.add_route('user.confirm', '/users/{uid}/confirm/{token}')
    config.add_route('user.edit', '/users/{uid}/edit')
    config.add_route('user.permissions', '/users/{uid}/permissions')
    config.add_route('user.delete', '/users/{uid}/delete')

@view_config(route_name='users')
@render({'text/html': 'users/list.html'})
@current_user()
def users(request):
    if is_authorised(u':user.has_permission("admin.users")', {'user': request.current_user}):
        pass
    else:
        unauthorised_redirect(request)
    return {}

class PasswordValidator(formencode.FancyValidator):
    
    messages = {'nologin': 'No user exists with the given e-mail address or the password does not match',
                'noconfirmed': 'You must confirm your registration before being able to log in'}
    
    def _validate_python(self, value, state):
        user = state.dbsession.query(User).filter(User.email==value['email']).first()
        if user:
            if user.validation_token:
                raise formencode.api.Invalid(self.message('noconfirmed', state), value, state)
            elif not user.password_matches(value['password']):
                raise formencode.api.Invalid(self.message('nologin', state), value, state)
        else:
            raise formencode.api.Invalid(self.message('nologin', state), value, state)
    
class LoginSchema(formencode.Schema):
    
    return_to = formencode.validators.UnicodeString(if_missing=None)
    email = formencode.validators.Email(not_empty=True)
    password = formencode.validators.UnicodeString(not_empty=True)
    
    chained_validators = [PasswordValidator()]
    
@view_config(route_name='user.login')
@render({'text/html': 'users/login.html'})
@current_user()
def login(request):
    if request.current_user.logged_in:
        request.session.flash('You are already logged in', queue='info')
        if 'return_to' in request.params and request.params['return_to'] != request.current_route_url():
            raise HTTPSeeOther(request.params['return_to'])
        else:
            raise HTTPSeeOther(request.route_url('root'))
    if request.method == 'POST':
        try:
            dbsession = DBSession()
            params = LoginSchema().to_python(request.params, State(dbsession=dbsession))
            user = dbsession.query(User).filter(User.email==params['email']).first()
            request.current_user = user
            request.current_user.logged_in = True
            request.session['uid'] = user.id
            request.session.flash('Welcome, %s' % (user.display_name), queue='info')
            if 'return_to' in request.params and request.params['return_to'] != request.current_route_url():
                raise HTTPSeeOther(request.params['return_to'])
            else:
                raise HTTPSeeOther(request.route_url('root'))
        except formencode.api.Invalid as e:
            e.params = request.params
            return {'e': e}
    return {}

@view_config(route_name='user.logout')
@render({'text/html': 'users/logout.html'})
@current_user()
def logout(request):
    if request.method == 'POST':
        request.current_user.logged_in = False
        request.session.delete()
        raise HTTPSeeOther(request.route_url('root'))
    return {}

class UniqueEmailValidator(formencode.FancyValidator):
    
    messages = {'existing': 'A user with this e-mail address already exists'}
    
    def _validate_python(self, value, state):
        user = state.dbsession.query(User).filter(User.email==value).first()
        if user and (not hasattr(state, 'userid') or user.id != state.userid):
            raise formencode.Invalid(self.message('existing', state), value, state)
    

class RegisterSchema(formencode.Schema):
    
    return_to = formencode.validators.UnicodeString(if_missing=None)
    email = formencode.All(formencode.validators.Email(not_empty=True),
                           UniqueEmailValidator())
    email_confirm = formencode.validators.Email(not_empty=True)
    name = formencode.validators.UnicodeString(not_empty=True)
    
    chained_validators = [formencode.validators.FieldsMatch('email',
                                                 'email_confirm')]

@view_config(route_name='user.register')
@render({'text/html': 'users/register.html'})
@current_user()
def register(request):
    if request.method == 'POST':
        try:
            dbsession = DBSession()
            params = RegisterSchema().to_python(request.params, State(dbsession=dbsession))
            with transaction.manager:
                user = User(params['email'], params['name'])
                user.validation_token = uuid.uuid4().get_hex()
                dbsession.add(user)
            dbsession.add(user)
            send_email(request,
                       user.email,
                       get_config_setting(request, 'email.sender',
                                          default='no-reply@example.com'),
                       'Please confirm your registration',
                       '''Hello %s,
                       
Thank you for registering with the Web Teaching Environment. To complete your registration, please click on the following link or copy it into your browser:

%s

Best Regards,
Web Teaching Environment''' % (user.display_name, request.route_url('user.confirm', uid=user.id, token=user.validation_token)))
            request.session.flash('Your registration has been successful. A confirmation e-mail has been sent to the e-mail address you specified.')
            raise HTTPSeeOther(request.route_url('root'))
        except formencode.Invalid as e:
            e.params = request.params
            return {'e': e}
    return {}

@view_config(route_name='user.confirm')
@render({'text/html': 'users/confirm.html'})
@current_user()
def confirm(request):
    dbsession = DBSession()
    user = dbsession.query(User).filter(and_(User.id==request.matchdict['uid'],
                                             User.validation_token==request.matchdict['token'])).first()
    if user:
        status = u'success'
        with transaction.manager:
            user.validation_token = None
            new_password = user.random_password()
        dbsession.add(user)
        send_email(request,
                   user.email,
                   get_config_setting(request, 'email.sender',
                                      default='no-reply@example.com'),
                   'Log in to the Web Teaching Environment',
                   '''Hello %s,
                       
Thank you for confirming your registration with the Web Teaching Environment. You can now log in using the following credentials:

Username: %s
Password: %s

Best Regards,
Web Teaching Environment''' % (user.display_name, user.email, new_password))
    else:
        user = dbsession.query(User).filter(and_(User.id==request.matchdict['uid'],
                                                 User.validation_token==None)).first()
        if user:
            status = u'confirmed'
        else:
            status = u'fail'
    return {'status': status}

class ForgottenPasswordSchema(formencode.Schema):
    email = formencode.validators.Email(not_empty=True)
    
@view_config(route_name='user.forgotten_password')
@render({'text/html': 'users/forgotten_password.html'})
@current_user()
def forgotten_password(request):
    if request.method == 'POST':
        dbsession = DBSession()
        try:
            params = ForgottenPasswordSchema().to_python(request.params)
            user = dbsession.query(User).filter(User.email==params['email']).first()
            if user:
                if user.validation_token:
                    with transaction.manager:
                        dbsession.add(user)
                        user.validation_token = uuid.uuid4().get_hex()
                    dbsession.add(user)
                    send_email(request,
                               user.email,
                               get_config_setting(request, 'email.sender',
                                                  default='no-reply@example.com'),
                               'Please confirm your registration',
                               '''Hello %s,
                       
Thank you for registering with the Web Teaching Environment. To complete your registration, please click on the following link or copy it into your browser:

%s

Best Regards,
Web Teaching Environment''' % (user.display_name, request.route_url('user.confirm', uid=user.id, token=user.validation_token)))
                    request.session.flash('A new confirmation e-mail has been sent to the specified e-mail address.', queue='info')
                    raise HTTPSeeOther(request.route_url('root'))
                else:
                    with transaction.manager:
                        dbsession.add(user)
                        new_password = user.random_password()
                    dbsession.add(user)
                    send_email(request,
                               user.email,
                               get_config_setting(request, 'email.sender',
                                                  default='no-reply@example.com'),
                               'Log in to the Web Teaching Environment',
                               '''Hello %s,

Thank you for confirming your registration with the Web Teaching Environment. You can now log in using the following credentials:

Username: %s
Password: %s

Best Regards,
Web Teaching Environment''' % (user.display_name, user.email, new_password))
                    request.session.flash('A new password has been sent to the specified e-mail address.', queue='info')
                    raise HTTPSeeOther(request.route_url('root'))
        except formencode.api.Invalid as e:
            e.params = request.params
            return {'e': e}
    return {}

@view_config(route_name='user.view')
@render({'text/html': 'users/view.html'})
@current_user()
def view(request):
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id==request.matchdict['uid']).first()
    if user:
        if is_authorised(u':user.allow("view" :current)', {'user': user,
                                                            'current': request.current_user}):
            return {'user': user}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

class EditSchema(formencode.Schema):
    
    email = formencode.All(formencode.validators.Email(not_empty=True),
                           UniqueEmailValidator())
    name = formencode.validators.UnicodeString(not_empty=True)
    password = formencode.validators.UnicodeString()
    
@view_config(route_name='user.edit')
@render({'text/html': 'users/edit.html'})
@current_user()
def edit(request):
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id==request.matchdict['uid']).first()
    if user:
        if is_authorised(u':user.allow("edit" :current)', {'user': user,
                                                            'current': request.current_user}):
            if request.method == 'POST':
                try:
                    params = EditSchema().to_python(request.params, State(dbsession=dbsession, userid=user.id))
                    with transaction.manager:
                        dbsession.add(user)
                        user.email = params['email']
                        user.name = params['name']
                        if params['password']:
                            user.new_password(params['password'])
                    request.session.flash('Profile updated', queue='info')
                    raise HTTPSeeOther(request.route_url('user.view', uid=request.matchdict['uid']))
                except formencode.api.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'user': user}
            return {'user': user}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='user.permissions')
@render({'text/html': 'users/permissions.html'})
@current_user()
def permissions(request):
    if is_authorised(u':user.has_permission("admin.users.permissions")', {'user': request.current_user}):
        dbsession = DBSession()
        user = dbsession.query(User).filter(User.id==request.matchdict['uid']).first()
        if user:
            permission_groups = dbsession.query(PermissionGroup).order_by(PermissionGroup.title)
            permissions = dbsession.query(Permission).order_by(Permission.title)
            if request.method == 'POST':
                with transaction.manager:
                    dbsession.add(user)
                    ids = request.params.getall('permission_group')
                    if ids:
                        user.permission_groups = dbsession.query(PermissionGroup).filter(PermissionGroup.id.in_(ids)).all()
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
                    'permissions': permissions}
        else:
            raise HTTPNotFound()
    else:
        unauthorised_redirect(request)

@view_config(route_name='user.delete')
@render({'text/html': 'users/delete.html'})
@current_user()
def delete(request):
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id==request.matchdict['uid']).first()
    if user:
        if is_authorised(u':user.allow("delete" :current)', {'user': user,
                                                             'current': request.current_user}):
            if request.method == 'POST':
                with transaction.manager:
                    dbsession.delete(user)
                request.session.flash('The account has been deleted', queue='info')
                raise HTTPSeeOther(request.route_url('root'))
            return {'user': user}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
