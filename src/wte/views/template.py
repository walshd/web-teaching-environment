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
    
    * ``template.new`` -- ``/modules/{mid}/tutorials/{tid}/templates/new`` --
      :func:`~wte.views.template.new`
    * ``template.edit`` -- ``/modules/{mid}/tutorials/{tid}/templates/{tpid}/edit``
      -- :func:`~wte.views.template.edit`
    * ``template.delete`` -- ``/modules/{mid}/tutorials/{tid}/templates/{tpid}/delete``
      -- :func:`~wte.views.template.delete`
    """
    config.add_route('template.new', '/modules/{mid}/tutorials/{tid}/templates/new')
    config.add_route('template.edit', '/modules/{mid}/tutorials/{tid}/templates/{tpid}/edit')
    config.add_route('template.delete', '/modules/{mid}/tutorials/{tid}/templates/{tpid}/delete')

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
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    if module and tutorial:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = TemplateSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(tutorial)
                        max_order = [t.order + 1 for t in tutorial.templates]
                        max_order.append(0)
                        max_order = max(max_order)
                        
                        new_template = Template(part_id=tutorial.id,
                                                filename=params['filename'],
                                                mimetype=params['mimetype'],
                                                content=u'',
                                                order=max_order)
                        dbsession.add(new_template)
                    dbsession.add(new_template)
                    request.session.flash('Your new template has been created', queue='info')
                    raise HTTPSeeOther(request.route_url('template.edit', mid=request.matchdict['mid'], tid=request.matchdict['tid'], tpid=new_template.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'tutorial': tutorial,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                                       {'title': 'Add template', 'url': request.route_url('template.new', mid=module.id, tid=tutorial.id), 'current': True}]}
            return {'module': module,
                    'tutorial': tutorial,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': 'Add template', 'url': request.route_url('template.new', mid=module.id, tid=tutorial.id), 'current': True}]}
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
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    template = dbsession.query(Template).filter(and_(Template.id==request.matchdict['tpid'],
                                                     Template.part_id==request.matchdict['tid'])).first()
    if module and tutorial and template:
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
                    request.session.flash('The template has been updated', queue='info')
                    raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=request.matchdict['tid']))
                except formencode.Invalid as e:
                    e.params = params
                    return {'e': e,
                            'module': module,
                            'tutorial': tutorial,
                            'template': template,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                                       {'title': 'Edit Template', 'url': request.route_url('template.edit', mid=module.id, tid=tutorial.id, tpid=template.id), 'current': True}]}
            return {'module': module,
                    'tutorial': tutorial,
                    'template': template,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': 'Edit Template', 'url': request.route_url('template.edit', mid=module.id, tid=tutorial.id, tpid=template.id), 'current': True}]}
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
    tutorial = dbsession.query(Part).filter(and_(Part.id==request.matchdict['tid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'tutorial')).first()
    template = dbsession.query(Template).filter(and_(Template.id==request.matchdict['tpid'],
                                                     Template.part_id==request.matchdict['tid'])).first()
    if module and tutorial and template:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                with transaction.manager:
                    dbsession.delete(template)
                request.session.flash('The template has been deleted', queue='info')
                raise HTTPSeeOther(request.route_url('tutorial.view', mid=request.matchdict['mid'], tid=request.matchdict['tid']))
            return {'module': module,
                    'tutorial': tutorial,
                    'template': template,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': tutorial.title, 'url': request.route_url('tutorial.view', mid=module.id, tid=tutorial.id)},
                               {'title': 'Delete Template', 'url': request.route_url('template.delete', mid=module.id, tid=tutorial.id, tpid=template.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
