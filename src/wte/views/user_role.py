# -*- coding: utf-8 -*-
u"""
########################################################
:mod:`wte.views.user_role` -- Backend for Users in Parts
########################################################

The :mod:`~wte.views.user_role` module provides the backend functionality for dealing with
:class:`~wte.models.User` that have are linked to a :class:`~wte.models.Part` via the
:class:`~wte.models.UserPartRole`.

Routes are defined in :func:`~wte.views.user_role.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import formencode
import math
import transaction

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools.renderer import render
from sqlalchemy import and_, or_

from wte.decorators import (current_user, require_logged_in)
from wte.models import (DBSession, Part, UserPartRole, User, UserPartProgress)
from wte.util import (unauthorised_redirect)
from wte.views.part import (create_part_crumbs, get_all_parts)


def init(config):
    u"""Adds the user-part-role-specific backend routes (route name, URL pattern
    handler):

    * ``part.users`` -- ``/parts/{pid}/users`` -- :func:`~wte.views.user_role.users`
    * ``part.users.action`` -- ``/parts/{pid}/users/action`` -- :func:`~wte.views.user_role.action`
    * ``part.users.update`` -- ``/parts/{pid}/users/update`` -- :func:`~wte.views.user_role.update`
    * ``part.users.add`` -- ``/parts/{pid}/users/add`` -- :func:`~wte.views.user_role.add`
    """
    config.add_route('part.users', '/parts/{pid}/users')
    config.add_route('part.users.action', '/parts/{pid}/users/action')
    config.add_route('part.users.update', '/parts/{pid}/users/update')
    config.add_route('part.users.add', '/parts/{pid}/users/add')


@view_config(route_name='part.users')
@render({'text/html': 'user_role/list.html'})
@current_user()
@require_logged_in()
def users(request):
    u"""Handles the ``parts/{pid}/users`` URL, displaying the
    :class:`~wte.models.User` registered for a :class:`~wte.models.Part`.

    Requires that the user has "users" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('users', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Users',
                                         'url': request.current_route_url()})
            try:
                start = int(request.params['start']) if 'start' in request.params else 0
            except:
                start = 0
            query = dbsession.query(UserPartRole).join(User)
            query_params = []
            if 'role' in request.params:
                if request.params['role'] == 'active':
                    query = query.filter(UserPartRole.role != u'block')
                elif request.params['role']:
                    query = query.filter(UserPartRole.role == request.params['role'])
                    query_params.append(('role', request.params['role']))
            else:
                query = query.filter(UserPartRole.role != u'block')
            if 'q' in request.params and request.params['q']:
                query = query.filter(or_(User.display_name.contains(request.params['q']),
                                         User.email.contains(request.params['q'])))
                query_params.append(('q', request.params['q']))
            total_users = query.count()
            if total_users < start:
                start = 0
            if start >= 0:
                users = query.offset(start).limit(30)
            else:
                users = query
            if total_users:
                pages = [{'title': 'Show all',
                          'url': request.route_url('part.users',
                                                   pid=part.id,
                                                   _query=query_params + [('start', '-1')]),
                          'class': 'current' if start < 0 else None}]
            else:
                pages = []
            if start < 0:
                pages.append({'title': 'Show page:',
                              'url': '#',
                              'class': 'unavailable'})
            for idx in range(0, int(math.ceil(total_users / 30.0))):
                pages.append({'title': unicode(idx + 1),
                              'url': request.route_url('part.users',
                                                       pid=part.id,
                                                       _query=query_params + [('start', idx * 30)]),
                              'class': 'current' if idx == (start / 30) else None})
            current_page = max(0, start / 30)
            return {'part': part,
                    'users': users,
                    'pages': pages,
                    'current_page': current_page,
                    'total_users': total_users,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class ActionSchema(formencode.Schema):
    u"""The :class:`~wte.views.user_role.ActionSchema` handles the
    validation of a actions applied in :func:`~wte.views.user_role.action` and
    :func:`~wte.views.user_role.update`.
    """
    action = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf(['block', 'remove', 'change_role']))
    u"""The action to apply"""
    role_id = formencode.ForEach(formencode.validators.Int(not_empty=True),
                                 convert_to_list=True,
                                 if_missing=formencode.api.NoDefault,
                                 not_empty=True)
    u"""The list of :class:`~wte.models.UserPartRole` to apply the action to"""
    allow_extra_fields = True


@view_config(route_name='part.users.action')
@render({'text/html': 'user_role/action.html'})
@current_user()
@require_logged_in()
def action(request):
    u"""Handles the ``parts/{pid}/users/action`` URL, loads the interface for changing
    :class:`~wte.models.User` registered for a :class:`~wte.models.Part`.

    Requires that the user has "users" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('users', request.current_user):
            try:
                params = ActionSchema().to_python(request.params)
            except formencode.api.Invalid:
                request.session.flash('Please select the action you wish to apply ' +
                                      'and the users you wish to apply it to', queue='error')
                raise HTTPSeeOther(request.route_url('part.users', pid=part.id))
            crumbs = create_part_crumbs(request,
                                        part,
                                        [{'title': 'Users',
                                         'url': request.route_url('part.users', pid=part.id)},
                                         {'title': 'Update',
                                          'url': request.current_route_url()}])
            users = dbsession.query(UserPartRole).filter(UserPartRole.id.in_(params['role_id'])).all()
            return {'part': part,
                    'params': params,
                    'users': users,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class ChangeRoleSchema(formencode.Schema):
    u"""The :class:`~wte.views.user_role.ChangeRoleSchema` handles the
    validation of a "change_role" action applied in :func:`~wte.views.user_role.update`.
    """
    action = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf(['change_role']))
    u"""The action to apply"""
    role_id = formencode.ForEach(formencode.validators.Int(not_empty=True),
                                 convert_to_list=True,
                                 if_missing=formencode.api.NoDefault,
                                 not_empty=True)
    u"""The list of :class:`~wte.models.UserPartRole` to apply the action to"""
    role = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                          formencode.validators.OneOf(['owner', 'tutor', 'student']))
    u"""The new role"""


@view_config(route_name='part.users.update')
@render({'text/html': 'user_role/action.html'})
@current_user()
@require_logged_in()
def update(request):
    u"""Handles the ``parts/{pid}/users`` URL, applying the changes select when the
    user views :func:`~wte.views.user_role.action`.

    Requires that the user has "users" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    dbsession.add(request.current_user)
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('users', request.current_user):
            try:
                params = ActionSchema().to_python(request.params)
            except formencode.api.Invalid:
                request.session.flash('Please select the action you wish to apply ' +
                                      'and the users you wish to apply it to', queue='error')
                raise HTTPSeeOther(request.route_url('part.users', pid=part.id))
            crumbs = create_part_crumbs(request,
                                        part,
                                        [{'title': 'Users',
                                         'url': request.route_url('part.users', pid=part.id)},
                                         {'title': 'Update',
                                          'url': request.current_route_url()}])
            users = dbsession.query(UserPartRole).filter(UserPartRole.id.in_(params['role_id'])).all()
            try:
                if params['action'] == 'change_role':
                    params = ChangeRoleSchema().to_python(request.params)
                    with transaction.manager:
                        for role in users:
                            dbsession.add(role)
                            role.role = params['role']
                    request.session.flash("The users' roles have been updated", queue='info')
                    raise HTTPSeeOther(request.route_url('part.users', pid=request.matchdict['pid']))
                elif params['action'] == 'remove':
                    with transaction.manager:
                        dbsession.add(part)
                        parts = get_all_parts(part)
                        for role in users:
                            for child_part in parts:
                                progress = dbsession.query(UserPartProgress).\
                                    filter(and_(UserPartProgress.part_id == child_part.id,
                                                UserPartProgress.user_id == role.user.id)).first()
                                if progress:
                                    dbsession.delete(progress)
                            dbsession.delete(role)
                    request.session.flash('The users have been removed', queue='info')
                    raise HTTPSeeOther(request.route_url('part.users', pid=request.matchdict['pid']))
                elif params['action'] == 'block':
                    with transaction.manager:
                        for role in users:
                            dbsession.add(role)
                            role.role = u'block'
                    request.session.flash('The users have been blocked', queue='info')
                    raise HTTPSeeOther(request.route_url('part.users', pid=request.matchdict['pid']))
            except formencode.api.Invalid as e:
                e.params = request.params
                return {'e': e,
                        'part': part,
                        'params': params,
                        'users': users,
                        'crumbs': crumbs}
            return {'part': part,
                    'params': params,
                    'users': users,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class AddUserSchema(formencode.Schema):
    u"""The :class:`~wte.views.user_role.AddUserSchema` handles the
    validation of a adding a :class:`~wte.models.User` to a
    :class:`~wte.models.Part`..
    """
    user_id = formencode.ForEach(formencode.validators.Int(not_empty=True),
                                 convert_to_list=True)
    u"""The id of the :class:`~wte.models.User` to add"""
    role = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                          formencode.validators.OneOf(['owner', 'tutor', 'student']))
    u"""The new role for the :class:`~wte.models.User`"""
    q = formencode.validators.UnicodeString(not_empty=False)
    u"""Save the query in case there are validation errors"""
    start = formencode.validators.Int(not_empty=False, if_missing=0)
    u"""Save the pagination in case there are validation errors"""


@view_config(route_name='part.users.add')
@render({'text/html': 'user_role/add.html'})
@current_user()
@require_logged_in()
def add(request):
    u"""Handles the ``parts/{pid}/users/add`` URL, providing the functionality for adding a
    :class:`~wte.models.User` to a :class:`~wte.models.Part`.

    Requires that the user has "users" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('users', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        [{'title': 'Users',
                                         'url': request.route_url('part.users', pid=part.id)},
                                         {'title': 'Add',
                                          'url': request.current_route_url()}])
            users = None
            if 'q' in request.params:
                users = dbsession.query(User).outerjoin(UserPartRole).\
                    filter(or_(User.display_name.contains(request.params['q']),
                               User.email.contains(request.params['q']))).\
                    filter(UserPartRole.id == None)
            start = 0
            if 'start' in request.params:
                try:
                    start = max(0, int(request.params['start']))
                except:
                    pass
            if users:
                total_users = users.count()
                users = users.offset(start).limit(20).all()
            else:
                total_users = 0
            pages = [i for i in range(0, int(math.ceil(total_users / 20.0)))]
            if request.method == 'POST':
                try:
                    params = AddUserSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(part)
                        for user_id in params['user_id']:
                            if not dbsession.query(UserPartRole).\
                                filter(and_(UserPartRole.part_id == part.id,
                                            UserPartRole.user_id == user_id)).first():
                                dbsession.add(UserPartRole(user_id=user_id,
                                                           part_id=part.id,
                                                           role=params['role']))
                    request.session.flash('The users have been added to the module', queue='info')
                    raise HTTPSeeOther(request.route_url('part.users', pid=request.matchdict['pid']))
                except formencode.api.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'part': part,
                            'users': users,
                            'total_users': total_users,
                            'start': start,
                            'pages': pages,
                            'crumbs': crumbs}
            return {'part': part,
                    'users': users,
                    'total_users': total_users,
                    'start': start,
                    'pages': pages,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()