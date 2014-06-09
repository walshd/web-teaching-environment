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

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised
from sqlalchemy import and_

from wte.decorators import current_user
from wte.util import (unauthorised_redirect)
from wte.models import (DBSession, Module, Part)

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
    config.add_route('part.new', '/modules/{mid}/parts/new')
    config.add_route('part.edit', '/modules/{mid}/parts/{pid}/edit')
    config.add_route('part.delete', '/modules/{mid}/parts/{pid}/delete')


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
    type = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                          formencode.validators.OneOf([u'tutorial',
                                                       u'page',
                                                       u'exercise',
                                                       u'task']))
    u"""The part's status"""
    

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
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    parent = dbsession.query(Part).filter(Part.id==request.params[u'parent_id']).first() if u'parent_id' in request.params else None
    if module:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if parent:
                if parent.type == u'tutorial':
                    available_types = [('page', 'Page')]
                elif parent.type == u'exercise':
                    available_types = [('task', 'Task')]
                else:
                    available_types = []
            else:
                available_types = [('tutorial', 'Tutorial'), ('exercise', 'Exercise')]
            crumbs = [{'title': 'Modules', 'url': request.route_url('modules')},
                      {'title': module.title, 'url': request.route_url('module.view', mid=module.id)}]
            tmp = parent
            while tmp:
                crumbs.insert(2, {'title': tmp.title, 'url': request.route_url('part.view', mid=module.id, pid=tmp.id)})
                tmp = tmp.parent
            crumbs.append({'title': 'Add Part', 'url': request.route_url('part.new', mid=module.id), 'current': True})
            if request.method == u'POST':
                try:
                    params = NewPartSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(module)
                        if parent:
                            dbsession.add(parent)
                            max_order = [p.order + 1 for p in parent.children]
                        else:
                            max_order = [p.order + 1 for p in module.parts]
                        max_order.append(0)
                        max_order = max(max_order)
                        
                        new_part = Part(title=params['title'],
                                        status=params['status'],
                                        type=params['type'],
                                        parent=parent,
                                        module=module,
                                        order=max_order)
                        dbsession.add(new_part)
                    dbsession.add(new_part)
                    request.session.flash('Your new %s has been created' % (params['type']), queue='info')
                    raise HTTPSeeOther(request.route_url('part.edit', mid=request.matchdict['mid'], pid=new_part.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'available_types': available_types,
                            'crumbs': crumbs}
            return {'module': module,
                    'available_types': available_types,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


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
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(and_(Part.id==request.matchdict['pid'],
                                             Part.module_id==request.matchdict['mid'])).first()
    if module and part:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            crumbs = [{'title': 'Modules', 'url': request.route_url('modules')},
                      {'title': module.title, 'url': request.route_url('module.view', mid=module.id)}]
            tmp = part
            while tmp:
                crumbs.insert(2, {'title': tmp.title, 'url': request.route_url('part.view', mid=module.id, pid=tmp.id)})
                tmp = tmp.parent
            crumbs.append({'title': 'Edit', 'url': request.current_route_url(), 'current': True})
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
                                                                               Part.module_id == request.matchdict['mid'])).first()
                                if child_part:
                                    child_part.order = idx
                    dbsession.add(part)
                    request.session.flash('The %s has been updated' % (part.type), queue='info')
                    raise HTTPSeeOther(request.route_url('part.view', mid=request.matchdict['mid'], pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'part': part,
                            'crumbs': crumbs}
            return {'module': module,
                    'part': part,
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
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(and_(Part.id==request.matchdict['pid'],
                                             Part.module_id==request.matchdict['mid'])).first()
    if module and part:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            crumbs = [{'title': 'Modules', 'url': request.route_url('modules')},
                      {'title': module.title, 'url': request.route_url('module.view', mid=module.id)}]
            tmp = part
            while tmp:
                crumbs.insert(2, {'title': tmp.title, 'url': request.route_url('part.view', mid=module.id, pid=tmp.id)})
                tmp = tmp.parent
            crumbs.append({'title': 'Delete', 'url': request.route_url('part.delete', mid=module.id, pid=part.id), 'current': True})
            if request.method == u'POST':
                part_type = part.type
                parent = part.parent
                with transaction.manager:
                    dbsession.delete(part)
                request.session.flash('The %s has been deleted' % (part_type), queue='info')
                if parent:
                    dbsession.add(parent)
                    raise HTTPSeeOther(request.route_url('part.view', mid=request.matchdict['mid'], pid=parent.id))
                else:
                    raise HTTPSeeOther(request.route_url('module.view', mid=request.matchdict['mid']))
            return {'module': module,
                    'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
