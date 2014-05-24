# -*- coding: utf-8 -*-
u"""
#########################################
:mod:`wte.views.module` -- Module Backend
#########################################

The :mod:`~wte.views.modle` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Module`.

Routes are defined in :func:`~wte.views.module.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction
import formencode

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools.auth import is_authorised

from wte.decorators import current_user
from wte.util import (unauthorised_redirect)
from wte.models import (DBSession, Module)

def init(config):
    u"""Adds the module-specific backend routes (route name, URL pattern
    handler):
    
    * ``module.new`` -- ``/modules/new`` -- :func:`~wte.views.module.new`
    * ``module.edit`` -- ``/modules/{mid}/edit`` --
      :func:`~wte.views.module.edit`
    * ``module.delete`` -- ``/modules/{mid}/delete``
      -- :func:`~wte.views.module.delete`
    """
    config.add_route('module.new', '/modules/new')
    config.add_route('module.edit', '/modules/{mid}/edit')
    config.add_route('module.delete', '/modules/{mid}/delete')

class ModuleSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.ModuleSchema` handles the validation
    of a new :class:`~wte.models.Module`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    u"""The module's title"""
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf([u'unavailable',
                                                         u'available']))
    u"""The module's status"""
    part_id = formencode.foreach.ForEach(formencode.validators.Int())
    u"""The ids of the child parts"""
    
@view_config(route_name='module.new')
@render({'text/html': 'module/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/new`` URL, providing the UI and backend for
    creating a new :class:`~wte.models.Module`.
    
    Requires that the user has "modules.create"
    :class:`~wte.models.Permission`.
    """
    if is_authorised(u':user.has_permission("modules.create")', {'user': request.current_user}):
        if request.method == u'POST':
            try:
                params = ModuleSchema().to_python(request.params)
                dbsession = DBSession()
                with transaction.manager:
                    new_module = Module(title=params['title'],
                                        status=params['status'],
                                        owner=request.current_user)
                    dbsession.add(new_module)
                dbsession.add(new_module)
                request.session.flash('Your new module has been created', queue='info')
                raise HTTPSeeOther(request.route_url('module.view', mid=new_module.id))
            except formencode.Invalid as e:
                e.params = request.params
                return {'e': e,
                        'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                        {'title': 'New', 'url': request.route_url('module.new'), 'current': True}]}
        return {'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                           {'title': 'New', 'url': request.route_url('module.new'), 'current': True}]}
    else:
        unauthorised_redirect(request)

@view_config(route_name='module.edit')
@render({'text/html': 'module/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/edit`` URL, providing the UI and backend
    for editing a :class:`~wte.models.Module`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    if module:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = ModuleSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(module)
                        module.title = params['title']
                        module.status = params['status']
                        if params['part_id']:
                            for order, tid in enumerate(params['part_id']):
                                for part in module.parts:
                                    if part.id == int(tid):
                                        dbsession.add(part)
                                        part.order = order
                    request.session.flash('The module has been updated', queue='info')
                    raise HTTPSeeOther(request.route_url('module.view', mid=request.matchdict['mid']))
                except formencode.Invalid as e:
                    e.params = params
                    return {'e': e,
                            'module': module,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': 'Edit', 'url': request.route_url('module.edit', mid=module.id), 'current': True}]}
            return {'module': module,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': 'Edit', 'url': request.route_url('module.edit', mid=module.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
    
@view_config(route_name='module.delete')
@render({'text/html': 'module/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/delete`` URL, providing the UI and backend
    for deleting a :class:`~wte.models.Module`.
    
    Requires that the user has "delete" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    if module:
        if is_authorised(u':module.allow("delete" :current)', {'module': module,
                                                               'current': request.current_user}):
            if request.method == u'POST':
                with transaction.manager:
                    dbsession.delete(module)
                request.session.flash('The module has been deleted', queue='info')
                raise HTTPSeeOther(request.route_url('modules'))
            return {'module': module,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': 'Delete', 'url': request.route_url('module.delete', mid=module.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
