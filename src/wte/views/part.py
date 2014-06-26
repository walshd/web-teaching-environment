# -*- coding: utf-8 -*-
u"""
#####################################
:mod:`wte.views.part` -- Part Backend
#####################################

The :mod:`~wte.views.part` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Part`.

Routes are defined in :func:`~wte.views.part.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction
import formencode

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound, HTTPForbidden)
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools import text
from sqlalchemy import and_

from wte.decorators import current_user
from wte.models import (DBSession, Part, UserPartRole, Asset, UserPartProgress)
from wte.text_formatter import compile_rst
from wte.util import (unauthorised_redirect)

def init(config):
    u"""Adds the part-specific backend routes (route name, URL pattern
    handler):
    
    * ``part.new`` -- ``/modules/{mid}/parts/new`` --
      :func:`~wte.views.part.new`
    * ``part.edit`` -- ``/modules/{mid}/parts/{pid}/edit`` --
      :func:`~wte.views.part.edit`
    * ``part.delete`` -- ``/modules/{mid}/parts/{pid}/delete``
      -- :func:`~wte.views.part.delete`
    """
    config.add_route('part.new', '/parts/new/{new_type}')
    config.add_route('part.edit', '/parts/{pid}/edit')
    config.add_route('part.delete', '/parts/{pid}/delete')
    config.add_route('part.preview', '/parts/{pid}/rst_preview')
    config.add_route('part.register', '/parts/{pid}/register')
    config.add_route('part.deregister', '/parts/{pid}/deregister')


class NewPartSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.NewPartSchema` handles the validation
    of a new :class:`~wte.models.Part`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    u"""The part's title"""
    parent_id = formencode.validators.Int(if_missing=None)
    u"""The parent :class:`~wte.models.Part`"""
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf([u'unavailable',
                                                         u'available']))
    u"""The part's status"""
    

def create_part_crumbs(request, part, current):
    crumbs = []
    while part:
        crumbs.append({'title': part.title,
                          'url': request.route_url('part.view', pid=part.id)})
        part = part.parent
    crumbs.append({'title': 'Modules',
                   'url': request.route_url('modules')})
    crumbs.reverse()
    if current:
        crumbs.append(current)
    crumbs[-1]['current'] = True
    return crumbs


@view_config(route_name='part.new')
@render({'text/html': 'part/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/{mid}/parts/new`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Part`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    parent = dbsession.query(Part).filter(Part.id==request.params[u'parent_id']).first() if u'parent_id' in request.params else None
    if parent and not parent.allow('edit', request.current_user):
            unauthorised_redirect(request)
    if request.matchdict['new_type'] == 'module':
        if not request.current_user.has_permission('modules.create'):
            raise unauthorised_redirect(request)
        elif parent:
            request.session.flash('You cannot create a new module here', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    elif request.matchdict['new_type'] == 'tutorial':
        if not parent:
            request.session.flash('You cannot create a new tutorial without a parent', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
        elif parent.type != u'module':
            request.session.flash('You can only add tutorials to a module', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    elif request.matchdict['new_type'] == 'page':
        if not parent:
            request.session.flash('You cannot create a new tutorial without a parent', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
        elif parent.type != u'tutorial':
            request.session.flash('You can only add pages to a tutorial', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    elif request.matchdict['new_type'] == 'exercise':
        if not parent:
            request.session.flash('You cannot create a new exercise without a parent', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
        elif parent.type != u'module':
            request.session.flash('You can only add exercises to a module', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    elif request.matchdict['new_type'] == 'task':
        if not parent:
            request.session.flash('You cannot create a new task without a parent', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
        elif parent.type != u'exercise':
            request.session.flash('You can only add tasks to a task', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    else:
        request.session.flash('You cannot create a new part of that type', queue='error')
        raise HTTPSeeOther(request.route_url('modules'))
    crumbs = create_part_crumbs(request,
                                parent,
                                {'title': 'Add %s' % (text.title(request.matchdict['new_type'])),
                                 'url': request.current_route_url()})
    if request.method == u'POST':
        try:
            params = NewPartSchema().to_python(request.params)
            dbsession = DBSession()
            with transaction.manager:
                if parent:
                    dbsession.add(parent)
                    max_order = [p.order + 1 for p in parent.children]
                else:
                    max_order = []
                max_order.append(0)
                max_order = max(max_order)
                
                new_part = Part(title=params['title'],
                                status=params['status'],
                                type=request.matchdict['new_type'],
                                parent=parent,
                                order=max_order)
                if request.matchdict['new_type'] == 'module':
                    new_part.users.append(UserPartRole(user=request.current_user,
                                                       role=u'owner'))
                dbsession.add(new_part)
            dbsession.add(new_part)
            request.session.flash('Your new %s has been created' % (request.matchdict['new_type']), queue='info')
            raise HTTPSeeOther(request.route_url('part.edit', pid=new_part.id))
        except formencode.Invalid as e:
            e.params = request.params
            return {'e': e,
                    'crumbs': crumbs}
    return {'crumbs': crumbs}


class EditPartSchema(formencode.Schema):
    u"""The :class:`~wte.views.part.EditPartSchema` handles the validation
    for editing :class:`~wte.models.Part`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    u"""The part's title"""
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf([u'unavailable',
                                                         u'available']))
    u"""The part's status"""
    content = formencode.validators.UnicodeString(not_empty=True)
    u"""The ReST content"""
    child_part_id = formencode.ForEach(formencode.validators.Int, if_missing=None)
    u"""The child :class:`~wte.models.Part` ids for re-ordering"""
    template_id = formencode.ForEach(formencode.validators.Int, if_missing=None)
    u"""The :class:`~wte.models.Template` ids for re-ordering"""


@view_config(route_name='part.edit')
@render({'text/html': 'part/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/edit`` URL,
    providing the UI and backend for editing a :class:`~wte.models.Part`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Edit',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                try:
                    params = EditPartSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(part)
                        part.title = params['title']
                        part.status = params['status']
                        part.content = params['content']
                        if params['child_part_id']:
                            for idx, cpid in enumerate(params['child_part_id']):
                                child_part = dbsession.query(Part).filter(and_(Part.id == cpid,
                                                                               Part.parent_id == part.id)).first()
                                if child_part:
                                    child_part.order = idx
                        if params['template_id']:
                            for idx, tid in enumerate(params['template_id']):
                                template = dbsession.query(Asset).filter(Asset.id == tid).first()
                                if template:
                                    template.order = idx
                    dbsession.add(part)
                    request.session.flash('The %s has been updated' % (part.type), queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'part': part,
                            'crumbs': crumbs}
            return {'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.delete')
@render({'text/html': 'part/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/delete`` URL, providing
    the UI and backend for deleting a :class:`~wte.models.Part`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict['pid']).first()
    if part:
        if part.allow('delete', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Delete',
                                         'url': request.route_url('part.delete',
                                                                  pid=part.id)})
            if request.method == u'POST':
                part_type = part.type
                parent = part.parent
                with transaction.manager:
                    dbsession.delete(part)
                request.session.flash('The %s has been deleted' % (part_type), queue='info')
                if parent:
                    dbsession.add(parent)
                    raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
                else:
                    raise HTTPSeeOther(request.route_url('modules'))
            return {'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.preview')
@render({'application/json': True})
@current_user()
def preview(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}/preview`` URL,
    generating an HTML preview of the submitted ReST. The ReST text to render
    has to be set as the ``content`` parameter.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            if 'content' in request.params:
                return {'content': compile_rst(request.params['content'])}
            else:
                raise HTTPNotFound()
        else:
            raise HTTPForbidden()
    else:
        raise HTTPNotFound()


@view_config(route_name='part.register')
@render({'text/html': 'part/register.html'})
@current_user()
def register(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}/preview`` URL,
    generating an HTML preview of the submitted ReST. The ReST text to render
    has to be set as the ``content`` parameter.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict['pid']).first()
    if part:
        if part.type != 'module':
            request.session.flash('You can only register for modules', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        if part.has_role(['student', 'owner'], request.current_user):
            request.session.flash('You are already registered for this module', queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        crumbs = create_part_crumbs(request,
                                    part,
                                    {'title': 'Register',
                                     'url': request.route_url('part.register',
                                                              pid=part.id)})
        if request.method == 'POST':
            with transaction.manager:
                dbsession.add(UserPartRole(user=request.current_user,
                                           part=part,
                                           role=u'student'))
            request.session.flash('You have registered for the module', queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        return {'part': part,
                'crumbs': crumbs}
    else:
        raise HTTPNotFound()


def get_all_parts(part):
    parts = [part]
    for child in part.children:
        parts.extend(get_all_parts(child))
    return parts


@view_config(route_name='part.deregister')
@render({'text/html': 'part/deregister.html'})
@current_user()
def deregister(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/pages/{pid}/preview`` URL,
    generating an HTML preview of the submitted ReST. The ReST text to render
    has to be set as the ``content`` parameter.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict['pid']).first()
    if part:
        if not part.has_role('student', request.current_user):
            request.session.flash('You are not registered for this module', queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        crumbs = create_part_crumbs(request,
                                    part,
                                    {'title': 'De-Register',
                                     'url': request.route_url('part.deregister',
                                                              pid=part.id)})
        if request.method == 'POST':
            with transaction.manager:
                dbsession.add(part)
                role = dbsession.query(UserPartRole).filter(and_(UserPartRole.part_id == request.matchdict['pid'],
                                                                 UserPartRole.user_id == request.current_user.id,
                                                                 UserPartRole.role == u'student')).first()
                if role:
                    dbsession.delete(role)
                parts = get_all_parts(part)
                for child_part in parts:
                    progress = dbsession.query(UserPartProgress).filter(and_(UserPartProgress.part_id == child_part.id,
                                                                             UserPartProgress.user_id == request.current_user.id)).first()
                    if progress:
                        dbsession.delete(progress)
            request.session.flash('You have de-registered from the module', queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        return {'part': part,
                'crumbs': crumbs}
    else:
        raise HTTPNotFound()
