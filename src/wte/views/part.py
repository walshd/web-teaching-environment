# -*- coding: utf-8 -*-
"""
#####################################
:mod:`wte.views.part` -- Part Backend
#####################################

The :mod:`~wte.views.part` module provides the functionality for
creating, viewing, editing, and deleting :class:`~wte.models.Part`.

Routes are defined in :func:`~wte.views.part.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from nine import (IS_PYTHON2, str, native_str, nimport)  # Python 2.7 compatibility

import formencode
import math
import json
import re
import transaction

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound, HTTPForbidden)
from pyramid.response import Response
from pyramid.renderers import render_to_response
from pyramid.view import view_config
from pywebtools.formencode import State, CSRFSchema
from pywebtools.pyramid.auth.decorators import unauthorised_redirect, require_logged_in
from pywebtools.pyramid.auth.views import current_user
from pywebtools.pyramid.decorators import require_method
from pywebtools.sqlalchemy import DBSession
from pkg_resources import resource_string
from sqlalchemy import and_
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, BadZipfile

from wte.models import (Part, UserPartRole, Asset, UserPartProgress, User,
                        Quiz, QuizAnswer)
from wte.text_formatter import compile_rst
from wte.util import (ordered_counted_set)
from wte.views.quiz import extract_quizzes

BytesIO = nimport('io:BytesIO')


def init(config):
    """Adds the part-specific backend routes (route name, URL pattern
    handler):

    * ``part.list`` -- ``/parts`` -- :func:`~wte.views.part.list_parts`
    * ``part.new`` -- ``/parts/new`` --
      :func:`~wte.views.part.new`
    * ``part.search`` -- ``/parts/search`` --
      :func:`~wte.views.part.search`
    * ``part.import`` -- ``/parts/import`` --
      :func:`~wte.views.part.import_file`
    * ``part.view`` -- ``/parts/{pid}`` --
      :func:`~wte.views.frontend.view_part`
    * ``part.edit`` -- ``/parts/{pid}/edit`` --
      :func:`~wte.views.part.edit`
    * ``part.delete`` -- ``/parts/{pid}/delete``
      -- :func:`~wte.views.part.delete`
    * ``part.delete`` -- ``/parts/{pid}/delete``
      -- :func:`~wte.views.part.delete`
    * ``part.preview`` -- ``/parts/{pid}/rst_preview`` --
      :func:`~wte.views.part.preview`
    * ``part.register`` -- ``/parts/{pid}/register``
      -- :func:`~wte.views.part.register`
    * ``part.register.settings`` -- ``/parts/{pid}/register/settings``
      -- :func:`~wte.views.part.edit_register_settings`
    * ``part.deregister`` -- ``/parts/{pid}/deregister``
      -- :func:`~wte.views.part.deregister`
    * ``part.change_status`` -- ``/parts/{pid}/change_status``
      -- :func:`~wte.views.part.change_status`
    * ``part.export`` -- ``/parts/{pid}/export``
      -- :func:`~wte.views.part.export`
    * ``part.download`` -- ``/parts/{pid}/download``
      -- :func:`~wte.views.part.download`
    * ``part.reset-files`` -- ``/parts/{pid}/reset_files`` --
      :func:`~wte.views.part.reset_files`
    * ``part.progress.download`` -- ``/parts/{pid}/progress/download``
      -- :func:`~wte.views.part.download_part_progress`
    * ``part.progress.update`` -- ``/parts/{pid}/progress/update``
      -- :func:`~wte.views.part.update_part_progress`
    """
    config.add_route('part.list', '/parts')
    config.add_route('part.new', '/parts/new/{new_type}')
    config.add_route('part.import', '/parts/import')
    config.add_route('part.search', '/parts/search')
    config.add_route('part.view', '/parts/{pid}')
    config.add_route('part.edit', '/parts/{pid}/edit')
    config.add_route('part.delete', '/parts/{pid}/delete')
    config.add_route('part.preview', '/parts/{pid}/rst_preview')
    config.add_route('part.register', '/parts/{pid}/register')
    config.add_route('part.register.settings', '/parts/{pid}/register/settings')
    config.add_route('part.deregister', '/parts/{pid}/deregister')
    config.add_route('part.change_status', '/parts/{pid}/change_status')
    config.add_route('part.export', '/parts/{pid}/export')
    config.add_route('part.download', '/parts/{pid}/download')
    config.add_route('part.reset-files', '/parts/{pid}/reset_files')
    config.add_route('part.progress.download', '/parts/{pid}/progress/download')
    config.add_route('part.progress.update', '/parts/{pid}/progress/update')


def get_user_part_progress(dbsession, user, part):
    """Returns the :class:`~wte.models.UserPartProgress` for the given
    ``user`` and ``part. If none exists, then a new one is instantiated. If
    the :class:`~wte.models.UserPartProgress` points to a current page that
    is different to ``page``, then the :class:`~wte.models.UserPartProgress`
    is updated.

    :param user: The user to get the progress for
    :type user: :class:`~wte.models.User`
    :param part: The part to get the progress for
    :type part: :class:`~wte.models.Part`
    :return: The :class:`~wte.models.UserPartProgress`
    :rtype: :class:`~wte.models.UserPartProgress`
    """
    if part.type == 'part':
        progress = dbsession.query(UserPartProgress).\
            filter(and_(UserPartProgress.user_id == user.id,
                        UserPartProgress.part_id == part.id)).first()
        if not progress:
            progress = UserPartProgress(user_id=user.id,
                                        part_id=part.id)
    elif part.type == 'page':
        progress = dbsession.query(UserPartProgress).\
            filter(and_(UserPartProgress.user_id == user.id,
                        UserPartProgress.part_id == part.parent.id)).first()
        if not progress:
            progress = UserPartProgress(user_id=user.id,
                                        part_id=part.parent.id,
                                        current_id=part.id)
    else:
        progress = None
    if progress:
        with transaction.manager:
            dbsession.add(progress)
            dbsession.add(part)
            if progress.visited is None:
                progress.visited = {}
            if part.type == 'page':
                if str(part.id) not in progress.visited:
                    progress.visited[str(part.id)] = {'duration': 0}
                templates = part.parent.templates
                progress.current_id = part.id
            else:
                templates = part.templates
            for template in templates:
                found = False
                for user_file in progress.files:
                    if user_file.filename == template.filename and user_file.mimetype == template.mimetype:
                        found = True
                        break
                if not found:
                    user_file = Asset(filename=template.filename,
                                      mimetype=template.mimetype,
                                      order=template.order,
                                      data=template.data,
                                      type='file',
                                      etag=template.etag)
                    dbsession.add(user_file)
                    progress.files.append(user_file)
            for template in templates:
                for user_file in progress.files:
                    if user_file.filename == template.filename and user_file.mimetype == template.mimetype:
                        user_file.order = template.order
                        break
        dbsession.add(part)
        dbsession.add(progress)
        dbsession.add(user)
    return progress


@view_config(route_name='part.list', renderer='wte:templates/part/list.kajiki')
@current_user()
def list_parts(request):
    """Handles the ``/parts`` URL, displaying modules. If no parameters are specified,
    lists all available modules. If a "user_id" parameter is specified, lists all
    modules for that user.
    """
    dbsession = DBSession()
    if 'user_id' in request.params:
        user = dbsession.query(User).filter(User.id == request.params['user_id']).first()
        if user and (user.id == request.current_user.id or user.has_permission('admin.users.view')):
            if user.id == request.current_user.id:
                title = 'My Modules'
                missing = 'You have not registered for any modules.'
            else:
                title = '%s\'s Modules' % user.display_name
                missing = '%s has not registered for any modules.' % user.display_name
            parts = dbsession.query(Part).join(UserPartRole)
            status = ['available', 'unavailable']
            has_archived = dbsession.query(Part).\
                join(UserPartRole).filter(and_(Part.type == 'module',
                                               Part.status == 'archived',
                                               UserPartRole.user_id == request.params['user_id'])).count() > 0
            if has_archived and 'status' in request.params:
                if request.params['status'] == 'all':
                    status.append('archived')
                elif request.params['status'] == 'archived':
                    status = ['archived']
            parts = parts.filter(and_(Part.type == 'module',
                                      Part.status.in_(status),
                                      UserPartRole.user_id == request.params['user_id'])).order_by(Part.title)
            crumbs = [{'title': 'My Modules',
                       'url': request.route_url('part.list',
                                                _query={'user_id': request.params['user_id']}),
                       'current': True}]
            help_path = ['user', 'learner', 'my_modules.html']
        else:
            raise HTTPNotFound()
    else:
        title = 'Available Modules'
        parts = dbsession.query(Part).filter(and_(Part.type == 'module',
                                                  Part.status == 'available')).order_by(Part.title).all()
        missing = 'There are currently no modules available.'
        crumbs = [{'title': 'Modules', 'url': request.route_url('part.list'), 'current': True}]
        has_archived = False
        help_path = ['user', 'learner', 'modules.html']
    return {'parts': parts,
            'title': title,
            'missing': missing,
            'crumbs': crumbs,
            'has_archived': has_archived,
            'help': help_path}


@view_config(route_name='part.view')
@current_user()
@require_logged_in()
def view_part(request):
    """Handles the ``parts/{pid}`` URL, displaying the
    :class:`~wte.models.Part`.

    Requires that the user has "view" rights on the
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            crumbs = create_part_crumbs(request,
                                        part,
                                        None)
            quizzes = []
            stats = {}
            if part.type == 'page':
                template_path = 'wte:templates/part/view/%s.kajiki' % part.parent.display_mode
                if part.parent.display_mode == 'three_pane_html':
                    help_path = ['user', 'learner', 'html_editor_part.html']
                else:
                    help_path = ['user', 'learner', 'text_part.html']
            else:
                template_path = 'wte:templates/part/view/%s.kajiki' % part.type
                help_path = ['user', 'learner', 'module.html']
                # Quiz Summary Generation - @Todo Should be refactored. Perhaps into the quiz view?
                quiz_ids = {}
                for quiz in dbsession.query(Quiz).join(Part).\
                        filter(Quiz.part_id.in_([c.id for c in part.children])).order_by(Part.order):
                    quiz_ids[quiz.id] = len(quizzes)
                    quizzes.append({'id': quiz.id,
                                    'title': quiz.title,
                                    'questions': json.loads(quiz.questions)})
                if part.has_role('student', request.current_user):
                    if quiz_ids:
                        for answer in dbsession.query(QuizAnswer).\
                                filter(and_(QuizAnswer.quiz_id.in_(list(quiz_ids.keys())),
                                            QuizAnswer.user_id == request.current_user.id)):
                            quizzes[quiz_ids[answer.quiz_id]]['answered'] = True
                            for question in quizzes[quiz_ids[answer.quiz_id]]['questions']:
                                if question['name'] == answer.question:
                                    question['attempts'] = answer.attempts
                                    if answer.initial_correct:
                                        question['correct'] = True
                                        question['answer'] = json.loads(answer.initial_answer)
                                    elif answer.final_correct:
                                        question['correct'] = True
                                        question['answer'] = json.loads(answer.final_answer)
                                    else:
                                        question['correct'] = False
                                        if answer.final_answer:
                                            question['answer'] = json.loads(answer.final_answer)
                    quizzes = [quiz for quiz in quizzes if 'answered' in quiz]
                else:
                    student_count = dbsession.query(UserPartRole).filter(and_(UserPartRole.part_id == part.parent_id,
                                                                              UserPartRole.role == 'student')).count()
                    for quiz in quizzes:
                        for question in quiz['questions']:
                            question['correct'] = {'initial': 0,
                                                   'subsequent': 0,
                                                   'incorrect': 0,
                                                   'total': student_count}
                    if quiz_ids:
                        for answer in dbsession.query(QuizAnswer).\
                                filter(QuizAnswer.quiz_id.in_(list(quiz_ids.keys()))):
                            for question in quizzes[quiz_ids[answer.quiz_id]]['questions']:
                                if question['name'] == answer.question:
                                    if answer.initial_correct:
                                        question['correct']['initial'] = question['correct']['initial'] + 1
                                    elif answer.final_correct:
                                        question['correct']['subsequent'] = question['correct']['subsequent'] + 1
                                    else:
                                        question['correct']['incorrect'] = question['correct']['incorrect'] + 1
                # End Quiz Summary Generation
                # Stats Generation
                if part.has_role('student', request.current_user):
                    stats['visited'] = len(progress.visited)
                    stats['time'] = sum([page['duration'] for page in progress.visited.values()])\
                        if stats['visited'] > 0 else 0
                else:
                    progresses = dbsession.query(UserPartProgress).join(UserPartProgress.user, User.roles).\
                        filter(and_(UserPartProgress.part_id == part.id,
                                    UserPartRole.part_id == (part.parent_id if part.type == 'part' else part.id),
                                    UserPartRole.role == 'student'))
                    total_students = dbsession.query(UserPartRole).\
                        filter(and_(UserPartRole.part_id == (part.parent_id if part.type == 'part' else part.id),
                                    UserPartRole.role == 'student')).count()
                    if total_students > 0:
                        stats['students'] = {'total': total_students,
                                             'inprogress': 0,
                                             'completed': 0}
                        time_spent = []
                        for progress in progresses:
                            if len(progress.visited) == len([c for c in part.children if c.status == 'available']):
                                stats['students']['completed'] = stats['students']['completed'] + 1
                            elif len(progress.visited) > 0:
                                stats['students']['inprogress'] = stats['students']['inprogress'] + 1
                            if len(progress.visited) > 0:
                                time_spent.append(sum([p['duration'] for p in progress.visited.values()]))
                        if time_spent:
                            time_spent.sort()
                            first = math.floor(len(time_spent) * 0.25)
                            median = math.floor(len(time_spent) * 0.5)
                            third = math.floor(len(time_spent) * 0.75)
                            stats['time'] = {25: time_spent[first],
                                             50: time_spent[median],
                                             75: time_spent[third]}
                # End Stats Generation
            labels = [child.label.title() if child.label else child.type.title() for child in part.children]
            return render_to_response(template_path,
                                      {'part': part,
                                       'crumbs': crumbs,
                                       'progress': progress,
                                       'include_footer': part.type != 'page',
                                       'labels': ordered_counted_set(labels),
                                       'quizzes': quizzes,
                                       'stats': stats,
                                       'help': help_path},
                                      request=request)
        else:
            if part.type == 'module':
                unauthorised_redirect(request)
            else:
                raise HTTPSeeOther(request.route_url('part.view', pid=part.parent_id))
    else:
        raise HTTPNotFound()


class NewPartSchema(CSRFSchema):
    """The :class:`~wte.views.backend.NewPartSchema` handles the validation
    of a new :class:`~wte.models.Part`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    """The part's title"""
    parent_id = formencode.validators.Int(if_missing=None)
    """The parent :class:`~wte.models.Part`"""
    order = formencode.validators.Int(if_missing=None)
    """The optional order index to create the new :class:`~wte.models.Part` at"""
    status = formencode.All(formencode.validators.UnicodeString(if_empty='available', if_missing='available'),
                            formencode.validators.OneOf(['unavailable',
                                                         'available']))
    """The part's status"""
    display_mode = formencode.All(formencode.validators.UnicodeString(if_empty=None, if_missing=None),
                                  formencode.validators.OneOf([None,
                                                               'three_pane_html',
                                                               'text_only']))
    """The part's display mode"""
    label = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """The part's label"""


def create_part_crumbs(request, part, current=None):
    """Creates the list of breadcrumbs for a given ``part``. If the ``current`` is a ``list``,
    then all will be added to the end of the crumbs.

    :param part: The part to create the breadcrumbs to
    :type part: :class:`~wte.models.Part`
    :param current: The final, current breadcrumb
    :type current: ``dict`` or ``list``
    :return: A list of `dict` for use in the breadcrumbs
    :rtype: ``list``
    """
    crumbs = []
    recurse_part = part
    while recurse_part:
        crumbs.append({'title': recurse_part.title,
                       'url': request.route_url('part.view', pid=recurse_part.id)})
        recurse_part = recurse_part.parent
    if part:
        if request.current_user and request.current_user.logged_in:
            crumbs.append({'title': 'My Modules',
                           'url': request.route_url('part.list', _query={'user_id': request.current_user.id})})
        else:
            crumbs.append({'title': 'Modules',
                           'url': request.route_url('part.list')})
    crumbs.reverse()
    if current:
        if isinstance(current, list):
            crumbs.extend(current)
        else:
            crumbs.append(current)
    crumbs[-1]['current'] = True
    return crumbs


@view_config(route_name='part.new', renderer='wte:templates/part/new.kajiki')
@current_user()
@require_logged_in()
def new(request):
    """Handles the ``/parts/new`` URL, providing the UI and
    backend for creating a new :class:`~wte.models.Part`.

    The required permissions depend on the type of :class:`~wte.models.Part`
    to create:
    * `module` -- User permission "modules.create"
    * `tutorial` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `page` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `exercise` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `task` -- "edit" permission on the parent :class:`~wte.models.Part`
    """
    dbsession = DBSession()
    parent = dbsession.query(Part).\
        filter(Part.id == request.params['parent_id']).first()\
        if 'parent_id' in request.params else None
    if parent and not parent.allow('edit', request.current_user):
            unauthorised_redirect(request)
    if request.matchdict['new_type'] == 'module':
        if not request.current_user.has_permission('modules.create'):
            raise unauthorised_redirect(request)
        elif parent:
            request.session.flash('You cannot create a new module here', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    elif request.matchdict['new_type'] == 'part':
        if not parent:
            request.session.flash('You cannot create a new part without a parent', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
        elif parent.type != 'module':
            request.session.flash('You can only add parts to a module', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    elif request.matchdict['new_type'] == 'page':
        if not parent:
            request.session.flash('You cannot create a new page without a parent', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
        elif parent.type != 'part':
            request.session.flash('You can only add pages to a part', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
    else:
        request.session.flash('You cannot create a new part of that type', queue='error')
        raise HTTPSeeOther(request.route_url('part.list'))
    crumbs = create_part_crumbs(request,
                                parent,
                                {'title': 'Add %s' % (request.matchdict['new_type'].title()),
                                 'url': request.current_route_url()})
    help_path = ['user', 'teacher', request.matchdict['new_type'], 'new.html']
    if request.method == 'POST':
        try:
            params = NewPartSchema().to_python(request.params,
                                               State(request=request))
            dbsession = DBSession()
            with transaction.manager:
                if params['order'] is not None:
                    max_order = params['order']
                    if parent:
                        dbsession.add(parent)
                        for child in parent.children:
                            if child.order >= max_order:
                                dbsession.add(child)
                                child.order = child.order + 1
                else:
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
                                display_mode=params['display_mode'],
                                label=params['label'],
                                parent=parent,
                                order=max_order,
                                content='')
                if request.matchdict['new_type'] == 'module':
                    new_part.users.append(UserPartRole(user=request.current_user,
                                                       role='owner'))
                dbsession.add(new_part)
            dbsession.add(new_part)
            raise HTTPSeeOther(request.route_url('part.edit', pid=new_part.id))
        except formencode.Invalid as e:
            return {'errors': e.error_dict,
                    'values': request.params,
                    'crumbs': crumbs,
                    'help': help_path}
    return {'crumbs': crumbs,
            'help': help_path}


class EditPartSchema(CSRFSchema):
    """The :class:`~wte.views.part.EditPartSchema` handles the validation
    for editing :class:`~wte.models.Part`.
    """
    title = formencode.validators.UnicodeString(not_empty=True)
    """The part's title"""
    status = formencode.All(formencode.validators.UnicodeString(if_empty='available', if_missing='available'),
                            formencode.validators.OneOf(['unavailable',
                                                         'available']))
    """The part's status"""
    display_mode = formencode.All(formencode.validators.UnicodeString(if_empty=None, if_missing=None),
                                  formencode.validators.OneOf([None,
                                                               'three_pane_html',
                                                               'text_only']))
    """The part's display mode"""
    label = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """The part's label"""
    content = formencode.validators.UnicodeString(if_missing='')
    """The ReST content"""
    child_part_id = formencode.ForEach(formencode.validators.Int, if_missing=None)
    """The child :class:`~wte.models.Part` ids for re-ordering"""
    template_id = formencode.ForEach(formencode.validators.Int, if_missing=None)
    """The :class:`~wte.models.Template` ids for re-ordering"""


@view_config(route_name='part.edit', renderer='wte:templates/part/edit.kajiki')
@current_user()
@require_logged_in()
def edit(request):
    """Handles the ``/parts/{pid}/edit`` URL,
    providing the UI and backend for editing a :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Edit',
                                         'url': request.current_route_url()})
            help_path = ['user', 'teacher', part.type, 'edit.html']
            if request.method == 'POST':
                try:
                    params = EditPartSchema().to_python(request.params,
                                                        State(request=request))
                    with transaction.manager:
                        dbsession.add(part)
                        part.title = params['title']
                        part.status = params['status']
                        part.display_mode = params['display_mode']
                        part.content = params['content']
                        try:
                            part.compiled_content = compile_rst(params['content'],
                                                                request,
                                                                part=part)
                            extract_quizzes(dbsession, part)
                        except Exception as e:
                            msg = e.message.replace('<string>:', 'Invalid ReST: Line ').replace('(SEVERE/4) ', '')
                            msg = msg[:msg.find('\n')]
                            raise formencode.Invalid('Invalid ReST',
                                                     params['content'],
                                                     None,
                                                     error_dict={'content': msg})
                        part.label = params['label']
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
                    raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    dbsession.add(part)
                    return {'errors': e.error_dict,
                            'values': request.params,
                            'part': part,
                            'crumbs': crumbs,
                            'help': help_path}
            return {'part': part,
                    'crumbs': crumbs,
                    'help': help_path}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class RegisterSettingsSchema(CSRFSchema):
    """The :class:`~wte.views.part.RegisterSettingsSchema` handles the validation
    for modifying the ``access_rights`` of a :class:`~wte.models.Part`.
    """
    require = formencode.ForEach(formencode.validators.OneOf(['password', 'email_domains']))
    """Which access rights are required"""
    password = formencode.validators.UnicodeString(if_missing=None)
    """The password to use for access rights"""
    email_domains = formencode.validators.UnicodeString(if_missing=None)
    """The email domains that the user must belong to"""


@view_config(route_name='part.register.settings', renderer='wte:templates/part/register_settings.kajiki')
@current_user()
@require_logged_in()
def edit_register_settings(request):
    """Handles the ``/parts/{pid}/register/settings`` URL,
    providing the UI and backend for editing the settings for registering for
    a "module" type :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            if part.type != 'module':
                request.session.flash('Access rights can only be set on modules', queue='info')
                raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
            if part.access_rights:
                rights = json.loads(part.access_rights)
            else:
                rights = {}
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Access Settings',
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                try:
                    params = RegisterSettingsSchema().to_python(request.params,
                                                                State(request=request))
                    with transaction.manager:
                        rights = {}
                        if params['require']:
                            if 'password' in params['require'] and params['password']:
                                rights['password'] = params['password']
                            if 'email_domains' in params['require'] and params['email_domains']:
                                rights['email_domains'] = [ed.strip() for ed in params['email_domains'].split(',')]
                        part.access_rights = json.dumps(rights)
                        dbsession.add(part)
                    dbsession.add(part)
                    raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'valuse': request.params,
                            'part': part,
                            'crumbs': crumbs,
                            'rights': rights,
                            'help': ['user', 'teacher', 'module', 'access_settings.html']}
            return {'part': part,
                    'crumbs': crumbs,
                    'rights': rights,
                    'help': ['user', 'teacher', 'module', 'access_settings.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.delete', renderer='wte:templates/part/delete.kajiki')
@current_user()
@require_logged_in()
def delete(request):
    """Handles the ``/modules/{mid}/parts/{pid}/delete`` URL, providing
    the UI and backend for deleting a :class:`~wte.models.Part`.

    Requires that the user has "delete" rights on the :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('delete', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Delete',
                                         'url': request.route_url('part.delete',
                                                                  pid=part.id)})
            if request.method == 'POST':
                try:
                    CSRFSchema().to_python(request.params, State(request=request))
                    parent = part.parent
                    with transaction.manager:
                        dbsession.add(part)
                        for progress in dbsession.query(UserPartProgress).\
                                filter(UserPartProgress.current_id == part.id):
                            progress.current_id = None
                        dbsession.delete(part)
                    if parent:
                        dbsession.add(parent)
                        raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
                    else:
                        dbsession.add(request.current_user)
                        raise HTTPSeeOther(request.route_url('part.list',
                                                             _query={'user_id': request.current_user.id}))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'part': part,
                            'crumbs': crumbs,
                            'help': ['user', 'teacher', part.type, 'delete.html']}
            return {'part': part,
                    'crumbs': crumbs,
                    'help': ['user', 'teacher', part.type, 'delete.html']}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.preview', renderer='json')
@current_user()
@require_logged_in()
def preview(request):
    """Handles the ``/parts/{pid}/rst_preview`` URL, generating an HTML preview of
    the submitted ReST. The ReST text to render has to be set as the ``content`` parameter.

    In addition to rendering the ReST the in the same way that it is rendered when
    saving a :class:`~wte.models.Part`, this will also insert a <span id="focus"></span>
    at the current cursor position indicated by the string "§§§§§§§".

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            if 'content' in request.params:
                try:
                    content = compile_rst(request.params['content'], request, part=part, line_numbers=True)
                except Exception as e:
                    content = ['<div class="callout alert"><p>']
                    for line in e.message.split('\n'):
                        if line:
                            content.append(line)
                            content.append('<br />')
                        else:
                            content.append('</p><p>')
                    content.append('</p></div>')
                    content = ''.join(content).replace('<br /></p>', '</p>').\
                        replace('<string>:', 'Line ').replace('(SEVERE/4) ', '')
                return {'content': content}
            else:
                raise HTTPNotFound()
        else:
            raise HTTPForbidden()
    else:
        raise HTTPNotFound()


# Todo: CSRF Protection
@view_config(route_name='part.register', renderer='wte:templates/part/register.kajiki')
@current_user()
@require_logged_in()
def register(request):
    """Handles the ``/parts/{pid}/register`` URL, to allow users to register
    for a :class:`~wte.models.Part` that is a "module".
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.type != 'module':
            request.session.flash('You can only register for modules', queue='error')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        if part.has_role(['student', 'owner'], request.current_user):
            request.session.flash('You are already registered for this module', queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        if part.status != 'available':
            request.session.flash('You cannot register for this module as it is %s' % (part.status), queue='auth')
            raise HTTPSeeOther(request.route_url('part.list'))
        crumbs = create_part_crumbs(request,
                                    part,
                                    {'title': 'Register',
                                     'url': request.route_url('part.register',
                                                              pid=part.id)})
        if request.method == 'POST':
            if part.access_rights:
                rights = json.loads(part.access_rights)
                if rights:
                    if 'password' in rights and 'email_domains' in rights:
                        if request.current_user.email[request.current_user.email.find('@') + 1:]\
                                in rights['email_domains']:
                            if 'password' not in request.params or request.params['password'] != rights['password']:
                                e = formencode.Invalid('Please provide the correct password',
                                                       None,
                                                       None,
                                                       error_dict={'password': 'Please provide the correct password'})
                                e.params = request.params
                                return {'part': part,
                                        'crumbs': crumbs,
                                        'e': e}
                        else:
                            request.session.flash('''Unfortunately you cannot take this module as your e-mail address is not
in the list of authorised e-mail domains.''', queue='auth')
                            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
                    elif 'password' in rights:
                        if 'password' not in request.params or request.params['password'] != rights['password']:
                            return {'part': part,
                                    'crumbs': crumbs,
                                    'invalid_password': True}
                    elif 'email_domains' in rights:
                        if request.current_user.email[request.current_user.email.find('@') + 1:] \
                                not in rights['email_domains']:
                            request.session.flash('Unfortunately you cannot take this module as your e-mail address ' +
                                                  'is not in the list of authorised e-mail domains.''', queue='auth')
                            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
            with transaction.manager:
                dbsession.add(UserPartRole(user=request.current_user,
                                           part=part,
                                           role='student'))
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        return {'part': part,
                'crumbs': crumbs}
    else:
        raise HTTPNotFound()


def get_all_parts(part):
    """Recursively returns the :class:`~wte.models.Part` and all its children.

    :param part: The :class:`~wte.models.Part` for which to find it children
    :type part: :class:`~wte.models.Part`
    :return: The ``part`` and all its children
    :rtype: ``list``
    """
    parts = [part]
    for child in part.children:
        parts.extend(get_all_parts(child))
    return parts


# Todo: CSRF Protection
@view_config(route_name='part.deregister', renderer='wte:templates/part/deregister.kajiki')
@current_user()
@require_logged_in()
def deregister(request):
    """Handles the ``/parts/{pid}/deregister`` URL, to allow users to de-register
    from a :class:`~wte.models.Part` that is a "module".
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
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
                role = dbsession.query(UserPartRole).\
                    filter(and_(UserPartRole.part_id == request.matchdict['pid'],
                                UserPartRole.user_id == request.current_user.id,
                                UserPartRole.role == 'student')).first()
                if role:
                    dbsession.delete(role)
                parts = get_all_parts(part)
                for child_part in parts:
                    progress = dbsession.query(UserPartProgress).\
                        filter(and_(UserPartProgress.part_id == child_part.id,
                                    UserPartProgress.user_id == request.current_user.id)).first()
                    if progress:
                        dbsession.delete(progress)
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        return {'part': part,
                'crumbs': crumbs}
    else:
        raise HTTPNotFound()


class ChangeStatusSchema(CSRFSchema):
    """The :class:`~wte.views.part.ChangeStatusSchema` handles the validation
    for editing :class:`~wte.models.Part`.
    """
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf(['unavailable',
                                                         'available',
                                                         'archived']))
    """The part's status"""
    return_to = formencode.validators.String(if_missing=None)
    """Return to this URL"""


@view_config(route_name='part.change_status', renderer='wte:templates/part/change_status.kajiki')
@current_user()
@require_logged_in()
def change_status(request):
    """Handles the ``/parts/{pid}/change_status`` URL,
    providing the UI and backend for changing the status of a :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Change Status',
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                try:
                    params = ChangeStatusSchema().to_python(request.params,
                                                            State(request=request))
                    with transaction.manager:
                        dbsession.add(part)
                        part.status = params['status']
                    dbsession.add(part)
                    if params['return_to']:
                        raise HTTPSeeOther(params['return_to'])
                    else:
                        raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'values': request.params,
                            'part': part,
                            'crumbs': crumbs}
            return {'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


CROSSREF_PATTERN = re.compile(r':crossref:`(?:([0-9]+)|(?:(.*)<([0-9]+)>))`')


def crossref_replace(match, id_mapping):
    """The :func:`~wte.views.part.crossref_replace` function updates a single
    cross-reference ReST role identified by the ``match`` parameter with the
    correct new target part identifier from the ``id_mapping``. If the
    identifier in the current cross-reference is not in the ``id_mapping``,
    then it is replaced with the string 'external'.

    :param match: The regexp match
    :type match: :class:`~re.MatchObject`
    :param id_mapping: The identifier change mappings
    :type id_mapping: `dict`
    :return: The updated cross-reference
    :return_type: `string`
    """
    groups = match.groups()
    part_id = groups[0] if groups[0] else groups[2]
    title = None if groups[0] else groups[1]
    if part_id in id_mapping:
        if title:
            return ':crossref:`%s<%s>`' % (title, id_mapping[part_id])
        else:
            return ':crossref:`%s`' % (id_mapping[part_id])
    else:
        if title:
            return ':crossref:`%s<external>`' % (title)
        else:
            return ':crossref:`external`'


@view_config(route_name='part.export')
@current_user()
@require_logged_in()
def export(request):
    """Handles the ``/parts/{pid}/export`` URL, providing the UI and backend
    for exporting a :class:`~wte.models.Part`.

    The difference between exporting and downloading
    (:func:`~wte.views.part.download`) is that exporting creates an archive
    that can be imported into another WTE instance, while downloading creates
    an HTML version for offline viewing.

    Requires that the user has "edit" rights on the :class:`~wte.models.Part`.
    """
    def part_as_dict(part, assets, id_mapping):
        data = {'id': len(id_mapping),
                'type': part.type,
                'display_mode': part.display_mode,
                'label': part.label,
                'title': part.title,
                'status': part.status,
                'order': part.order,
                'content': part.content}
        id_mapping[str(part.id)] = data['id']
        if part.children:
            data['children'] = [part_as_dict(child, assets, id_mapping) for child in part.children]
        if part.all_assets:
            data['assets'] = []
            for asset in part.all_assets:
                data['assets'].append({'id': len(assets),
                                       'filename': asset.filename,
                                       'mimetype': asset.mimetype,
                                       'type': asset.type,
                                       'order': asset.order})
                assets.append((len(assets), asset.id))
        return data

    def fix_references(data, id_mapping):
        if 'content' in data and data['content']:
            data['content'] = re.sub(CROSSREF_PATTERN, lambda m: crossref_replace(m, id_mapping), data['content'])
        if 'children' in data:
            data['children'] = [fix_references(child, id_mapping) for child in data['children']]
        return data

    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Export',
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                body = BytesIO()
                body_zip = ZipFile(body, 'w')
                assets = []
                id_mapping = {}
                data = part_as_dict(part, assets, id_mapping)
                data = fix_references(data, id_mapping)
                body_zip.writestr('content.json', json.dumps(data), ZIP_DEFLATED)
                for export_id, asset_id in assets:
                    asset = dbsession.query(Asset).filter(Asset.id == asset_id).first()
                    if asset:
                        if asset.data:
                            if asset.mimetype.startswith('text'):
                                body_zip.writestr('assets/%s' % (export_id), asset.data, ZIP_DEFLATED)
                            else:
                                body_zip.writestr('assets/%s' % (export_id), asset.data, ZIP_STORED)
                        else:
                            body_zip.writestr('assets/%s' % (export_id), '', ZIP_DEFLATED)
                body_zip.close()
                return Response(body=body.getvalue(),
                                headers=[('Content-Type', 'application/zip'),
                                         ('Content-Disposition',
                                          native_str('attachment; filename="%s.zip"' % (part.title)))])

            return render_to_response('wte:templates/part/export.kajiki',
                                      {'part': part,
                                       'crumbs': crumbs,
                                       'help': ['user', 'teacher', 'import_export.html']},
                                      request=request)
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class ImportPartConverter(formencode.FancyValidator):
    """The :class:`~wte.views.part.ImportPartConverter` converts a :class:`~cgi.FieldStorage`
    into a (``dict``, :class:`~zipfile.ZipFile`) ``tuple``. Checks that the uploaded
    zip file is actually a valid file and that it can be imported with the given parent
    :class:`~wte.models.Part`. The ``dict`` contains the :class:`~wte.models.Part` data to
    import.
    """
    messages = {'notzip': 'Only ZIP files can be imported',
                'invalidstructure': 'The ZIP file does not have the correct internal structure',
                'nopart': 'The ZIP file does not contain any data to import',
                'invalidpart': 'You cannot import a %(part_type)s here'}

    def _convert_to_python(self, value, state):
        """Convert the submitted ``value`` into a (``dict``, :class:`~zipfile.ZipFile`)
        ``tuple``. Checks that the uploaded file is a valid ZIP file and contains the
        "content.json" file.

        :param value: The uploaded file
        :type value: `~cgi.FieldStorage`
        :param state: The state object
        :return: The converted part import data
        :rtype: (``dict``, :class:`~zipfile.ZipFile`) ``tuple``
        """
        try:
            zip_file = ZipFile(value.file)
            zip_file.getinfo('content.json')
            with zip_file.open('content.json') as data:
                data = data.read()
                if not IS_PYTHON2:
                    data = data.decode('utf-8')
            data = json.loads(data)
            return (data, zip_file)
        except BadZipfile:
            raise formencode.api.Invalid(self.message('notzip', state), value, state)
        except KeyError:
            zip_file.close()
            raise formencode.api.Invalid(self.message('invalidstructure', state), value, state)
        except ValueError:
            zip_file.close()
            raise formencode.api.Invalid(self.message('nopart', state), value, state)

    def _validate_python(self, value, state):
        """Checks that the uploaded "content.json" file is actually valid. Checks that the
        JSON data is catually a ``dict`` and that it has the minium fields "title" and "type".
        Also checks if there is a ``state.parent`` object, whether the :class:`~wte.models.Part`
        data to import can be imported into the ``state.parent`` :class:`~wte.models.Part`.
        """
        (data, zip_file) = value
        if not isinstance(data, dict):
            zip_file.close()
            raise formencode.api.Invalid(self.message('nopart', state), value, state)
        if 'title' not in data or 'type' not in data:
            zip_file.close()
            raise formencode.api.Invalid(self.message('nopart', state), value, state)
        if not state.parent and data['type'] != 'module':
            zip_file.close()
            raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']), value, state)
        if state.parent:
            if state.parent.type == 'module':
                if data['type'] not in ['tutorial', 'exercise', 'part']:
                    raise formencode.api.Invalid(self.message('invalidpart',
                                                              state,
                                                              part_type=data['type']),
                                                 value,
                                                 state)
            elif state.parent.type == 'part':
                if data['type'] != 'page':
                    raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                                 value,
                                                 state)
            elif state.parent.type == 'tutorial':  # Handle old "page" Part imports
                if data['type'] != 'page':
                    raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                                 value,
                                                 state)
            elif state.parent.type == 'exercise':  # Handle old "task" Part imports
                if data['type'] != 'task':
                    raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                                 value,
                                                 state)
            else:
                raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                             value,
                                             state)


class ImportPartSchema(CSRFSchema):
    """The :class:`~wte.views.part.ImportPartSchema` validates the request to import
    a :class:`~wte.models.Part` (and any children and :class:`~wte.models.Asset`).

    Uses the :class:`~wte.views.part.ImportPartConverter` to actually check whether the
    uploaded file is a valid export generated from :func:`~wte.views.part.export`.
    """

    parent_id = formencode.validators.Int(if_missing=None)
    """The id of the parent :class:`~wte.models.Part` to import into."""
    file = formencode.compound.Pipe(formencode.validators.FieldStorageUploadConverter(not_empty=True),
                                    ImportPartConverter())
    """The file to import."""


@view_config(route_name='part.import', renderer='wte:templates/part/import.kajiki')
@current_user()
@require_logged_in()
def import_file(request):
    """Handles the ``/parts/import`` URL, providing the UI and
    backend for importing a :class:`~wte.models.Part`.

    The required permissions depend on the type of :class:`~wte.models.Part`
    to create:
    * `module` -- User permission "modules.create"
    * `tutorial` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `page` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `exercise` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `task` -- "edit" permission on the parent :class:`~wte.models.Part`
    """
    def recursive_import(data, zip_file, id_mapping):
        part_type = data['type']
        if part_type == 'task':
            part_type = 'page'
        elif part_type in ['tutorial', 'exercise']:
            part_type = 'part'
        part = Part(type=part_type,
                    title=data['title'],
                    status='available' if part_type == 'page' else 'unavailable')
        if 'id' in data:
            id_mapping[str(data['id'])] = part
        if 'order' in data:
            try:
                part.order = int(data['order'])
            except ValueError:
                part.order = 0
        if 'content' in data:
            part.content = data['content']
        if part_type == 'part' and 'display_mode' in data:
            part.display_mode = data['display_mode']
        elif part_type == 'part':
            part.display_mode = 'three_pane_html'
        if 'label' in data:
            part.label = data['label']
        else:
            if data['type'] in ['tutorial', 'exercise', 'page', 'task']:
                part.label = data['type'].title()
        if 'assets' in data:
            for tmpl in data['assets']:
                if 'filename' in tmpl and 'mimetype' in tmpl and 'id' in tmpl and 'type' in tmpl:
                    try:
                        content = zip_file.open('assets/%i' % (tmpl['id']))
                        asset = Asset(filename=tmpl['filename'],
                                      mimetype=tmpl['mimetype'],
                                      data=content.read(),
                                      type=tmpl['type'])
                        if 'order' in tmpl:
                            try:
                                asset.order = int(tmpl['order'])
                            except ValueError:
                                asset.order = 0
                        part.all_assets.append(asset)
                    except:
                        pass
        if 'children' in data:
            for child in data['children']:
                child_part = recursive_import(child, zip_file, id_mapping)
                part.children.append(child_part)
                child_part.parent = part
        return part

    def fix_references(part, dbsession, id_mapping):
        dbsession.add(part)
        if part.content:
            part.content = re.sub(CROSSREF_PATTERN, lambda m: crossref_replace(m, id_mapping), part.content)
            part.compiled_content = compile_rst(part.content,
                                                request,
                                                part=part)
        if part.children:
            for child in part.children:
                fix_references(child, dbsession, id_mapping)

    dbsession = DBSession()
    parent = dbsession.query(Part).\
        filter(Part.id == request.params['parent_id']).first()\
        if 'parent_id' in request.params else None
    if parent and not parent.allow('edit', request.current_user):
        unauthorised_redirect(request)
    elif not parent and not request.current_user.has_permission('modules.create'):
        unauthorised_redirect(request)
    crumbs = create_part_crumbs(request,
                                parent,
                                {'title': 'Import',
                                 'url': request.current_route_url()})
    if request.method == 'POST':
        try:
            params = ImportPartSchema().to_python(request.params, State(parent=parent,
                                                                        request=request))
            with transaction.manager:
                if parent:
                    dbsession.add(parent)
                id_mapping = {}
                part = recursive_import(params['file'][0], params['file'][1], id_mapping)
                dbsession.add(part)
                params['file'][1].close()
                if part.type == 'module':
                    part.users.append(UserPartRole(user=request.current_user,
                                                   role='owner'))
                if parent:
                    parent.children.append(part)
            with transaction.manager:
                for key, value in list(id_mapping.items()):
                    dbsession.add(value)
                    id_mapping[key] = value.id
                fix_references(part, dbsession, id_mapping)
            dbsession.add(part)
            raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
        except formencode.Invalid as e:
            return {'errors': e.error_dict,
                    'valuse': request.params,
                    'crumbs': crumbs,
                    'help': ['user', 'teacher', 'import_export.html']}
    return {'crumbs': crumbs,
            'help': ['user', 'teacher', 'import_export.html']}


# Todo: Add a download launch page for non-JS users
@view_config(route_name='part.download')
@require_method('POST')
@current_user()
@require_logged_in()
def download(request):
    """Handles the ``/parts/{pid}/download`` URL, providing the UI and backend
    for downloading a :class:`~wte.models.Part`.

    The difference between exporting (:func:`~wte.views.part.export`) and
    downloading is that exporting creates an archive that can be imported into
    another WTE instance, while downloading creates an HTML version for
    offline viewing.
    """
    def download_part(base_path, part, body_zip, parents=None):
        response = render_to_response('wte:templates/part/download.kajiki',
                                      {'part': part,
                                       'parents': parents},
                                      request=request)
        body_zip.writestr('%s/%s.html' % (base_path, part.id), response.body)
        for child in part.children:
            if child.allow('view', request.current_user):
                download_part(base_path, child, body_zip, parents + [part] if parents else [part])
        for asset in part.assets:
            body_zip.writestr('%s/%s/assets/%s' % (base_path, part.id, asset.filename),
                              asset.data if asset.data else '')
        for template in part.templates:
            template_data = template.data if template.data else native_str('')
            body_zip.writestr('%s/%s/%s' % (base_path, part.id, template.filename), template_data)
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            body = BytesIO()
            body_zip = ZipFile(body, 'w')
            for target, source in [('%s/_static/application.min.css', 'static/css/application.min.css'),
                                   ('%s/_static/icons/foundation-icons.eot', 'static/css/icons/foundation-icons.eot'),
                                   ('%s/_static/icons/foundation-icons.svg', 'static/css/icons/foundation-icons.svg'),
                                   ('%s/_static/icons/foundation-icons.ttf', 'static/css/icons/foundation-icons.ttf'),
                                   ('%s/_static/icons/foundation-icons.woff', 'static/css/icons/foundation-icons.woff'),
                                   ('%s/_static/jquery.min.js', 'static/js/jquery.min.js')]:
                body_zip.writestr(target % part.title,
                                  native_str(resource_string('wte', source)))
            index_html = '''<!DOCTYPE html>
<html>
  <head>
    <title>%(title)s</title>
    <script>
      window.location.href = '%(url)s';
    </script>
    <meta http-equiv="refresh" content="1; url=%(url)s">
  </head>
  <body>
    <p>The main content can be found <a href="%(url)s">here</a></p>
  </body>
</html>''' % {'title': part.title, 'url': '%s.html' % part.id}
            if IS_PYTHON2:
                index_html = index_html.encode('utf-8')
            body_zip.writestr('%s/index.html' % (part.title), index_html)
            download_part(part.title, part, body_zip)
            body_zip.close()
            return Response(body=body.getvalue(),
                            headers=[('Content-Type', 'application/zip'),
                                     ('Content-Disposition',
                                      native_str('attachment; filename="%s.zip"' % (part.title)))])
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class ResetFilesSchema(CSRFSchema):
    """Validator for resetting all the files in the user's :class:`~wte.models.UserPartProgress`
    to their initial values."""

    filename = formencode.validators.UnicodeString(if_empty=None, if_missing=None)
    """The optional filename to reset."""


@view_config(route_name='part.reset-files', renderer='wte:templates/part/reset_files.kajiki')
@current_user()
@require_logged_in()
def reset_files(request):
    """Handles the ``/parts/{pid}/reset_files`` URL, providing
    the UI and backend for resetting all :class:`~wte.models.Assets` of a
    :class:`~wte.models.Part` to the default for the current user.

    Requires that the user has "view" rights on the current
    :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Discard all Changes',
                                         'url': request.current_route_url()})
            if request.method == 'POST':
                try:
                    params = ResetFilesSchema().to_python(request.params, State(request=request))
                    with transaction.manager:
                        progress = get_user_part_progress(dbsession, request.current_user, part)
                        for user_file in list(progress.files):
                            if not params['filename'] or params['filename'] == user_file.filename:
                                progress.files.remove(user_file)
                                dbsession.delete(user_file)
                    raise HTTPSeeOther(request.route_url('part.view',
                                                         pid=request.matchdict['pid']))
                except formencode.Invalid as e:
                    return {'errors': e.error_dict,
                            'part': part,
                            'crumbs': crumbs}
            return {'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.progress.download')
@current_user()
@require_logged_in()
def download_part_progress(request):
    """Handles the ``/users/{uid}/progress/{pid}/download``
    URL, sending back the complete set of data associated with the
    :class:`~wte.models.UserPartProgress`.

    Requires that the user has "view" rights on the
    :class:`~wte.models.UserPartProgress`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            basepath = progress.part.title
            filename = progress.part.title
            parent = progress.part.parent
            while parent:
                basepath = '%s/%s' % (parent.title, basepath)
                filename = '%s - %s' % (parent.title, filename)
                parent = parent.parent
            basepath = '%s/' % (basepath)
            filename = '%s.zip' % (filename)
            body = BytesIO()
            zipfile = ZipFile(body, mode='w')
            for user_file in progress.files:
                zipfile.writestr('%s%s' % (basepath, user_file.filename), user_file.data)
            for asset in progress.part.assets:
                zipfile.writestr('%s/assets/%s' % (basepath, asset.filename), asset.data)
            zipfile.close()
            return Response(body=body.getvalue(),
                            headerlist=[('Content-Type', 'application/zip'),
                                        ('Content-Disposition', 'attachment; filename="%s"' % (filename))])
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.progress.update', renderer='json')
@current_user()
@require_logged_in()
def update_part_progress(request):
    """Handles the ``/users/{uid}/progress/{pid}/download``
    URL, sending back the complete set of data associated with the
    :class:`~wte.models.UserPartProgress`.

    Requires that the user has "view" rights on the
    :class:`~wte.models.UserPartProgress`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    request.response.cache_control = 'no-cache'
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            if 'duration' in request.params:
                with transaction.manager:
                    dbsession.add(progress)
                    dbsession.add(part)
                    progress.visited[str(part.id)]['duration'] = progress.visited[str(part.id)]['duration'] +\
                        int(int(request.params['duration']) / 1000)
            return {}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.search', renderer='json')
@current_user()
@require_logged_in()
def search(request):
    """Handles the ``/parts/search`` URL, searching all
    :class:`~wte.models.Part` for matches to the request parameter 'q'.
    Returns all :class:`~wte.models.Part` that the current user is
    allowed to view.
    """
    dbsession = DBSession()
    parts = []
    if 'q' in request.params and request.params['q']:
        for part in dbsession.query(Part).filter(Part.title.like('%%%s%%' % request.params['q'])):
            if part.allow('view', request.current_user):
                parts.append({'id': part.id, 'value': part.title})
    return parts
