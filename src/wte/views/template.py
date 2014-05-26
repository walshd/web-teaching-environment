# -*- coding: utf-8 -*-
u"""
#############################################
:mod:`wte.views.template` -- Template Backend
#############################################

The :mod:`~wte.views.template` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Template`.

Routes are defined in :func:`~wte.views.template.init`.

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
from wte.models import (DBSession, Module, Part, Template)

def init(config):
    u"""Adds the template-specific backend routes (route name, URL pattern
    handler):
    
    * ``template.new`` -- ``/modules/{mid}/parts/{pid}/templates/new`` --
      :func:`~wte.views.template.new`
    * ``template.edit`` -- ``/modules/{mid}/parts/{pid}/templates/{tid}/edit``
      -- :func:`~wte.views.template.edit`
    * ``template.delete`` -- ``/modules/{mid}/parts/{pid}/templates/{tid}/delete``
      -- :func:`~wte.views.template.delete`
    """
    config.add_route('template.new', '/modules/{mid}/parts/{pid}/templates/new')
    config.add_route('template.edit', '/modules/{mid}/parts/{pid}/templates/{tid}/edit')
    config.add_route('template.delete', '/modules/{mid}/parts/{pid}/templates/{tid}/delete')

class TemplateSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.TemplateSchema` handles the validation
    of a new or updated :class:`~wte.models.Template`.
    """
    filename = formencode.validators.UnicodeString(not_empty=True)
    u"""The template's filename"""
    mimetype = formencode.validators.UnicodeString(not_empty=True)
    u"""The template's mimetype"""
    content = formencode.validators.UnicodeString(if_missing=u'')
    u"""The template's content"""
    
@view_config(route_name='template.new')
@render({'text/html': 'template/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/templates/new`` URL,
    providing the UI and backend for creating a new
    :class:`~wte.models.Template`.
    
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
            if request.method == u'POST':
                try:
                    params = TemplateSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(part)
                        max_order = [t.order + 1 for t in part.templates]
                        max_order.append(0)
                        max_order = max(max_order)
                        
                        new_template = Template(part_id=part.id,
                                                filename=params['filename'],
                                                mimetype=params['mimetype'],
                                                content=u'',
                                                order=max_order)
                        dbsession.add(new_template)
                    dbsession.add(new_template)
                    request.session.flash('Your new template has been created', queue='info')
                    raise HTTPSeeOther(request.route_url('template.edit', mid=request.matchdict['mid'], pid=request.matchdict['pid'], tid=new_template.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'part': part,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': part.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=part.id)} if part.type == 'tutorial' else {'title': part.title, 'url': request.route_url('exercise.view', mid=module.id, eid=part.id)},
                                       {'title': 'Add template', 'url': request.route_url('template.new', mid=module.id, pid=part.id), 'current': True}]}
            return {'module': module,
                    'part': part,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': part.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=part.id)} if part.type == 'tutorial' else {'title': part.title, 'url': request.route_url('exercise.view', mid=module.id, eid=part.id)},
                               {'title': 'Add template', 'url': request.route_url('template.new', mid=module.id, pid=part.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='template.edit')
@render({'text/html': 'template/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/templates/{pid}/edit``
    URL, providing the UI and backend for editing a
    :class:`~wte.models.Tutorial`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(and_(Part.id==request.matchdict['pid'],
                                             Part.module_id==request.matchdict['mid'])).first()
    template = dbsession.query(Template).filter(and_(Template.id==request.matchdict['tid'],
                                                     Template.part_id==request.matchdict['pid'])).first()
    if module and part and template:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = TemplateSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(template)
                        template.filename = params['filename']
                        template.mimetype = params['mimetype']
                        template.content = params['content']
                    dbsession.add(part)
                    request.session.flash('The template has been updated', queue='info')
                    if part.type == 'tutorial':
                        raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=request.matchdict['pid']))
                    else:
                        raise HTTPSeeOther(request.route_url('exercise.view', mid=request.matchdict['mid'], eid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    e.params = params
                    return {'e': e,
                            'module': module,
                            'part': part,
                            'template': template,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': part.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=part.id)} if part.type == 'tutorial' else {'title': part.title, 'url': request.route_url('exercise.view', mid=module.id, eid=part.id)},
                                       {'title': 'Edit Template', 'url': request.route_url('template.edit', mid=module.id, pid=part.id, tid=template.id), 'current': True}]}
            return {'module': module,
                    'part': part,
                    'template': template,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': part.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=part.id)} if part.type == 'tutorial' else {'title': part.title, 'url': request.route_url('exercise.view', mid=module.id, eid=part.id)},
                               {'title': 'Edit Template', 'url': request.route_url('template.edit', mid=module.id, pid=part.id, tid=template.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='template.delete')
@render({'text/html': 'template/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/tutorials/{tid}/templates/{pid}/delete``
    URL, providing the UI and backend for deleting a
    :class:`~wte.models.Template`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    part = dbsession.query(Part).filter(and_(Part.id==request.matchdict['pid'],
                                             Part.module_id==request.matchdict['mid'])).first()
    template = dbsession.query(Template).filter(and_(Template.id==request.matchdict['tid'],
                                                     Template.part_id==request.matchdict['pid'])).first()
    if module and part and template:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                with transaction.manager:
                    dbsession.delete(template)
                dbsession.add(part)
                request.session.flash('The template has been deleted', queue='info')
                if part.type == 'tutorial':
                    raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=request.matchdict['pid']))
                else:
                    raise HTTPSeeOther(request.route_url('exercise.view', mid=request.matchdict['mid'], eid=request.matchdict['pid']))
            return {'module': module,
                    'part': part,
                    'template': template,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': part.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=part.id)} if part.type == 'tutorial' else {'title': part.title, 'url': request.route_url('exercise.view', mid=module.id, eid=part.id)},
                               {'title': 'Delete Template', 'url': request.route_url('template.delete', mid=module.id, pid=part.id, tid=template.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
