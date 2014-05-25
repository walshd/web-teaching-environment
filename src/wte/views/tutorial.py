# -*- coding: utf-8 -*-
u"""
#############################################
:mod:`wte.views.tutorial` -- Tutorial Backend
#############################################

The :mod:`~wte.views.tutorial` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Part` when they are
set as type "tutorial".

Routes are defined in :func:`~wte.views.tutorial.init`.

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
    u"""Adds the tutorial-specific backend routes (route name, URL pattern
    handler):
    
    * ``tutorial.new`` -- ``/modules/{mid}/tutorials/new`` --
      :func:`~wte.views.tutorial.new`
    * ``tutorial.edit`` -- ``/modules/{mid}/tutorials/{tid}/edit`` --
      :func:`~wte.views.tutorial.edit`
    * ``tutorial.delete`` -- ``/modules/{mid}/tutorials/{tid}/delete`` --
      :func:`~wte.views.tutorial.delete`
    """
    config.add_route('tutorial.new', '/modules/{mid}/tutorials/new')
    config.add_route('tutorial.edit', '/modules/{mid}/tutorials/{tid}/edit')
    config.add_route('tutorial.delete', '/modules/{mid}/tutorials/{tid}/delete')

class TutorialSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.TutorialSchema` handles the validation
    of a new :class:`~wte.models.Part`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    u"""The exercise's title"""
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf([u'unavailable',
                                                         u'available']))
    u"""The exercise's status"""
    page_id = formencode.foreach.ForEach(formencode.validators.Int())
    u"""The ids of the child :class:`~wte.models.Part`"""
    template_id = formencode.foreach.ForEach(formencode.validators.Int())
    u"""The ids of the child :class:`~wte.models.Template`"""
    
@view_config(route_name='tutorial.new')
@render({'text/html': 'tutorial/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/{mid}/tutorials/new`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Part` as a "tutorial".
    
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
                    params = TutorialSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(module)
                        max_order = [t.order + 1 for t in module.parts]
                        max_order.append(0)
                        max_order = max(max_order)
                        
                        new_tutorial = Part(title=params['title'],
                                            status=params['status'],
                                            module=module,
                                            order=max_order,
                                            type=u'tutorial')
                        dbsession.add(new_tutorial)
                    dbsession.add(new_tutorial)
                    request.session.flash('Your new tutorial has been created', queue='info')
                    raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=new_tutorial.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': 'Add Tutorial', 'url': request.route_url('tutorial.new', mid=module.id), 'current': True}]}
            return {'module': module,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': 'Add Tutorial', 'url': request.route_url('tutorial.new', mid=module.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='tutorial.edit')
@render({'text/html': 'tutorial/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/edit`` URL, providing
    the UI and backend for editing a :class:`~wte.models.Part` as a "tutorial".
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    if module and tutorial:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = TutorialSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(tutorial)
                        tutorial.title = params['title']
                        tutorial.status = params['status']
                        if params['page_id']:
                            for order, pid in enumerate(params['page_id']):
                                for page in tutorial.pages:
                                    if page.id == int(pid):
                                        dbsession.add(page)
                                        page.order = order
                        if params['template_id']:
                            for order, tpid in enumerate(params['template_id']):
                                for template in tutorial.templates:
                                    if template.id == int(tpid):
                                        dbsession.add(template)
                                        template.order = order
                    request.session.flash('The tutorial has been updated', queue='info')
                    raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=request.matchdict['tid']))
                except formencode.Invalid as e:
                    e.params = params
                    return {'e': e,
                            'module': module,
                            'tutorial': tutorial,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                                       {'title': 'Edit', 'url': request.route_url('tutorial.edit', mid=module.id, tid=tutorial.id), 'current': True}]}
            return {'module': module,
                    'tutorial': tutorial,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': 'Edit', 'url': request.route_url('tutorial.edit', mid=module.id, tid=tutorial.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='tutorial.delete')
@render({'text/html': 'tutorial/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/delete`` URL, providing
    the UI and backend for deleting a :class:`~wte.models.Part` as a "tutorial".
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    if module and tutorial:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                with transaction.manager:
                    dbsession.delete(tutorial)
                request.session.flash('The tutorial has been deleted', queue='info')
                raise HTTPSeeOther(request.route_url('module.view', mid=request.matchdict['mid']))
            return {'module': module,
                    'tutorial': tutorial,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': 'Delete', 'url': request.route_url('tutorial.delete', mid=module.id, tid=tutorial.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
