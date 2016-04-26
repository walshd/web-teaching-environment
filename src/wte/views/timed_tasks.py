# -*- coding: utf-8 -*-
"""
###################################################
:mod:`wte.views.timed_tasks` -- Timed Tasks Backend
###################################################

The :mod:`~wte.views.timed_task` module provides the functionality for
creating, viewing, editing, and deleting :class:`~wte.models.TimedTask`.

Routes are defined in :func:`~wte.views.timed_tasks.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import formencode
import transaction

from datetime import datetime
from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound)
from pyramid.view import view_config

from wte.decorators import (current_user, require_logged_in)
from wte.models import (DBSession, Part, TimedTask)
from wte.util import (unauthorised_redirect, DateValidator, TimeValidator, DynamicSchema,
                      CSRFSchema, State)
from wte.views.part import create_part_crumbs


def init(config):
    """Adds the timed-task-specific backend routes (route name, URL pattern
    handler):

    * ``parts.timed_tasks`` -- ``/parts/{pid}/timed-tasks`` --
      :func:`~wte.views.timed_tasks.view_part_tasks`
    * ``parts.timed_tasks.new`` -- ``/parts/{pid}/timed-tasks/new`` --
      :func:`~wte.views.timed_tasks.new_part_task`
    * ``parts.timed_tasks.edit`` -- ``/parts/{pid}/timed-tasks/{tid}/edit`` --
      :func:`~wte.views.timed_tasks.edit_part_task`
    * ``parts.timed_tasks.delete`` -- ``/parts/{pid}/timed-tasks/{tid}/delete`` --
      :func:`~wte.views.timed_tasks.delete_part_task`
    """
    config.add_route('part.timed_task', '/parts/{pid}/timed-tasks')
    config.add_route('part.timed_task.new', '/parts/{pid}/timed-tasks/new')
    config.add_route('part.timed_task.edit', '/parts/{pid}/timed-tasks/{tid}/edit')
    config.add_route('part.timed_task.delete', '/parts/{pid}/timed-tasks/{tid}/delete')


@view_config(route_name='part.timed_task', renderer='wte:templates/timed_task/view.kajiki')
@current_user()
@require_logged_in()
def view_part_tasks(request):
    """Handles the ``parts/{pid}/timed-tasks`` URL, displaying the
    :class:`~wte.models.TimedTask`\ s for the given :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Edit Timed Actions',
                                         'url': request.current_route_url()})
            available_tasks = [('change_status', 'Change Status')]
            return {'part': part,
                    'crumbs': crumbs,
                    'available_tasks': available_tasks,
                    'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class NewTimedTaskSchema(CSRFSchema):
    """The :class:`~wte.views.timed_tasks.NewTimedTaskSchema` handles the
    validation of a new :class:`~wte.models.TimedTask`.
    """
    name = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                          formencode.validators.OneOf(['change_status']))
    """The new task's name"""


@view_config(route_name='part.timed_task.new', renderer='wte:templates/timed_task/new.kajiki')
@current_user()
@require_logged_in()
def new_part_task(request):
    """Handles the ``parts/{pid}/timed-tasks/new`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.TimedTask`\ s for
    a given :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Timed Actions',
                                         'url': request.current_route_url()})
            available_tasks = [('change_status', 'Change Status')]
            if request.method == 'POST':
                try:
                    params = NewTimedTaskSchema().to_python(request.params, State(request=request))
                    with transaction.manager:
                        title = 'Unknown Task'
                        if params['name'] == 'change_status':
                            title = 'Change Status'
                        new_task = TimedTask(name=params['name'],
                                             part_id=part.id,
                                             title=title,
                                             status='new')
                        dbsession.add(new_task)
                    dbsession.add(part)
                    dbsession.add(new_task)
                    raise HTTPSeeOther(request.route_url('part.timed_task.edit', pid=part.id, tid=new_task.id))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'values': request.params,
                            'part': part,
                            'crumbs': crumbs,
                            'available_tasks': available_tasks,
                            'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
            return {'part': part,
                    'crumbs': crumbs,
                    'available_tasks': available_tasks,
                    'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class EditTimedTaskSchema(CSRFSchema):
    """The :class:`~wte.views.timed_tasks.EditTimedTaskSchema` handles the
    validation of changes to a :class:`~wte.models.TimedTask`.

    By default it only expects to validate date (YYYY-MM-DDD) and time
    (HH:MM) fields. An additional ``options`` field is added, if the
    ``options`` parameter is passed to the constructor. In this case the
    :class:`~wte.views.timed_tasks.EditTimedTaskSchema` expects the additional
    field-names in the submitted form to have names in the format
    "options.{field-name}".
    """

    date = DateValidator(not_empty=True)
    """The task's updated date"""
    time = TimeValidator(not_empty=True)
    """The tasks's updatet time"""

    pre_validators = [formencode.variabledecode.NestedVariables()]

    def __init__(self, options=None, **kwargs):
        """:param options: Any additional option validators to apply.
        :type options: ``list`` of ``tuple`` (field-name, validator)"""
        formencode.Schema.__init__(self, **kwargs)
        if options:
            self.add_field('options', DynamicSchema(options))


@view_config(route_name='part.timed_task.edit', renderer='wte:templates/timed_task/edit.kajiki')
@current_user()
@require_logged_in()
def edit_part_task(request):
    """Handles the ``parts/{pid}/timed-tasks/{tid}/edit`` URL, providing the UI
    and backend for editing an existing :class:`~wte.models.TimedTask` that
    belongs to a :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    task = dbsession.query(TimedTask).filter(TimedTask.id == request.matchdict['tid']).first()
    if part and task:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        [{'title': 'Timed Actions',
                                         'url': request.route_url('part.timed_task', pid=part.id)},
                                         {'title': 'Edit',
                                          'url': request.current_route_url}])
            if request.method == 'POST':
                try:
                    options = []
                    if task.name == 'change_status':
                        status = ['available', 'unavailable']
                        if part.type == 'module':
                            status.append('archived')
                        options.append(('target_status', formencode.validators.OneOf(status)))
                    params = EditTimedTaskSchema(options).to_python(request.params, State(request=request))
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.add(task)
                        task.timestamp = datetime.combine(params['date'], params['time'])
                        if 'options' in params and params['options']:
                            task.options = params['options']
                            task.status = 'ready'
                    dbsession.add(part)
                    raise HTTPSeeOther(request.route_url('part.timed_task', pid=part.id))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'values': request.params,
                            'part': part,
                            'task': task,
                            'crumbs': crumbs,
                            'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
            return {'part': part,
                    'task': task,
                    'crumbs': crumbs,
                    'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.timed_task.delete', renderer='wte:templates/timed_task/delete.kajiki')
@current_user()
@require_logged_in()
def delete_part_task(request):
    """Handles the ``parts/{pid}/timed-tasks/{tid}/delete`` URL, providing the UI
    and backend for deleting an existing :class:`~wte.models.TimedTask` that
    belongs to a :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    task = dbsession.query(TimedTask).filter(TimedTask.id == request.matchdict['tid']).first()
    if part and task:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        [{'title': 'Timed Actions',
                                         'url': request.route_url('part.timed_task', pid=part.id)},
                                         {'title': 'Delete',
                                          'url': request.current_route_url}])
            if request.method == 'POST':
                try:
                    CSRFSchema().to_python(request.params, State(request=request))
                    dbsession = DBSession()
                    with transaction.manager:
                        dbsession.delete(task)
                    dbsession.add(part)
                    raise HTTPSeeOther(request.route_url('part.timed_task', pid=part.id))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'part': part,
                            'task': task,
                            'crumbs': crumbs,
                            'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
            return {'part': part,
                    'task': task,
                    'crumbs': crumbs,
                    'include_footer': True,
                    'help': ['user', 'teacher', 'timed_actions.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
