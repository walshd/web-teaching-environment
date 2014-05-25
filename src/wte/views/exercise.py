# -*- coding: utf-8 -*-
u"""
#############################################
:mod:`wte.views.exercise` -- Exercise Backend
#############################################

The :mod:`~wte.views.exercise` module provides the backend functionality for
creating, editing, and deleting :class:`~wte.models.Part` when they are used
as "exercises".

Routes are defined in :func:`~wte.views.exercise.init`.

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
    u"""Adds the exercise-specific backend routes (route name, URL pattern
    handler):
    
    * ``exercise.new`` -- ``/modules/{mid}/exercise/new`` --
      :func:`~wte.views.tutorial.new`
    * ``exercise.edit`` -- ``/modules/{mid}/exercise/{eid}/edit`` --
      :func:`~wte.views.tutorial.edit`
    * ``exercise.delete`` -- ``/modules/{mid}/exercise/{eid}/delete`` --
      :func:`~wte.views.tutorial.delete`
    """
    config.add_route('exercise.new', '/modules/{mid}/exercise/new')
    config.add_route('exercise.edit', '/modules/{mid}/exercise/{eid}/edit')
    config.add_route('exercise.delete', '/modules/{mid}/exercise/{eid}/delete')

class ExerciseSchema(formencode.Schema):
    u"""The :class:`~wte.views.backend.NewModuleSchema` handles the validation
    of a new :class:`~wte.models.Part` as an exercise.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    u"""The exercise's title"""
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf([u'unavailable',
                                                         u'available']))
    u"""The exercise's status"""
    
@view_config(route_name='exercise.new')
@render({'text/html': 'exercise/new.html'})
@current_user()
def new(request):
    u"""Handles the ``/modules/{mid}/exercises/new`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Part` as an exercise.
    
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
                    params = ExerciseSchema().to_python(request.params)
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(module)
                        max_order = [t.order + 1 for t in module.parts]
                        max_order.append(0)
                        max_order = max(max_order)
                        
                        new_exercise = Part(title=params['title'],
                                            status=params['status'],
                                            module=module,
                                            order=max_order,
                                            type=u'exercise')
                        dbsession.add(new_exercise)
                    dbsession.add(new_exercise)
                    request.session.flash('Your new exercise has been created', queue='info')
                    raise HTTPSeeOther(request.route_url('exercise.view', mid=request.matchdict['mid'], eid=new_exercise.id))
                except formencode.Invalid as e:
                    e.params = request.params
                    return {'e': e,
                            'module': module,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': 'Add Exercise', 'url': request.route_url('exercise.new', mid=module.id), 'current': True}]}
            return {'module': module,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': 'Add exercise', 'url': request.route_url('exercise.new', mid=module.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='exercise.edit')
@render({'text/html': 'exercise/edit.html'})
@current_user()
def edit(request):
    u"""Handles the ``/modules/{mid}/exercise/{eid}/edit`` URL, providing
    the UI and backend for editing a :class:`~wte.models.Part` as an
    exercise.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    exercise = dbsession.query(Part).filter(and_(Part.id==request.matchdict['eid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'exercise')).first()
    if module and exercise:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                try:
                    params = ExerciseSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(exercise)
                        exercise.title = params['title']
                        exercise.status = params['status']
                    request.session.flash('The exercise has been updated', queue='info')
                    raise HTTPSeeOther(request.route_url('exercise.view', mid=request.matchdict['mid'], eid=request.matchdict['eid']))
                except formencode.Invalid as e:
                    e.params = params
                    return {'e': e,
                            'module': module,
                            'exercise': exercise,
                            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                                       {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                                       {'title': exercise.title, 'url': request.route_url('exercise.view', mid=module.id, eid=exercise.id)},
                                       {'title': 'Edit', 'url': request.route_url('exercise.edit', mid=module.id, eid=exercise.id), 'current': True}]}
            return {'module': module,
                    'exercise': exercise,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': exercise.title, 'url': request.route_url('exercise.view', mid=module.id, eid=exercise.id)},
                               {'title': 'Edit', 'url': request.route_url('exercise.edit', mid=module.id, eid=exercise.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='exercise.delete')
@render({'text/html': 'exercise/delete.html'})
@current_user()
def delete(request):
    u"""Handles the ``/modules/{mid}/exercises/{eid}/delete`` URL, providing
    the UI and backend for deleting a :class:`~wte.models.Part`.
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    module = dbsession.query(Module).filter(Module.id==request.matchdict['mid']).first()
    exercise = dbsession.query(Part).filter(and_(Part.id==request.matchdict['eid'],
                                                 Part.module_id==request.matchdict['mid'],
                                                 Part.type==u'exercise')).first()
    if module and exercise:
        if is_authorised(u':module.allow("edit" :current)', {'module': module,
                                                             'current': request.current_user}):
            if request.method == u'POST':
                with transaction.manager:
                    dbsession.delete(exercise)
                request.session.flash('The exercise has been deleted', queue='info')
                raise HTTPSeeOther(request.route_url('module.view', mid=request.matchdict['mid']))
            return {'module': module,
                    'exercise': exercise,
                    'crumbs': [{'title': 'Modules', 'url': request.route_url('modules')},
                               {'title': module.title, 'url': request.route_url('module.view', mid=module.id)},
                               {'title': exercise.title, 'url': request.route_url('exercise.view', mid=module.id, eid=exercise.id)},
                               {'title': 'Delete', 'url': request.route_url('exercise.delete', mid=module.id, eid=exercise.id), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
