# -*- coding: utf-8 -*-
u"""
#####################################
:mod:`wte.views.part` -- Part Backend
#####################################

The :mod:`~wte.views.part` module provides the functionality for
creating, viewing, editing, and deleting :class:`~wte.models.Part`.

Routes are defined in :func:`~wte.views.part.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import formencode
import json
import transaction

from pyramid.httpexceptions import (HTTPSeeOther, HTTPNotFound, HTTPForbidden)
from pyramid.response import Response
from pyramid.view import view_config
from pywebtools.renderer import render
from pywebtools import text
from sqlalchemy import and_
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED, BadZipfile

from wte.decorators import (current_user, require_logged_in)
from wte.models import (DBSession, Part, UserPartRole, Asset, UserPartProgress)
from wte.text_formatter import compile_rst
from wte.util import (unauthorised_redirect, State)


def init(config):
    u"""Adds the part-specific backend routes (route name, URL pattern
    handler):

    * ``part.new`` -- ``/parts/new`` --
      :func:`~wte.views.part.new`
    * ``part.view`` -- ``/parts/{pid}`` --
      :func:`~wte.views.frontend.view_part`
    * ``part.edit`` -- ``/parts/{pid}/edit`` --
      :func:`~wte.views.part.edit`
    * ``part.delete`` -- ``/parts/{pid}/delete``
      -- :func:`~wte.views.part.delete`
    * ``part.delete`` -- ``/parts/{pid}/delete``
      -- :func:`~wte.views.part.delete`
    * ``part.register`` -- ``/parts/{pid}/register``
      -- :func:`~wte.views.part.register`
    * ``part.deregister`` -- ``/parts/{pid}/deregister``
      -- :func:`~wte.views.part.deregister`
    """
    config.add_route('part.new', '/parts/new/{new_type}')
    config.add_route('part.import', '/parts/import')
    config.add_route('part.view', '/parts/{pid}')
    config.add_route('part.edit', '/parts/{pid}/edit')
    config.add_route('part.delete', '/parts/{pid}/delete')
    config.add_route('part.preview', '/parts/{pid}/rst_preview')
    config.add_route('part.register', '/parts/{pid}/register')
    config.add_route('part.deregister', '/parts/{pid}/deregister')
    config.add_route('part.change_status', '/parts/{pid}/change_status')
    config.add_route('part.export', '/parts/{pid}/export')


def get_user_part_progress(dbsession, user, part):
    u"""Returns the :class:`~wte.models.UserPartProgress` for the given
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
    if part.type in [u'tutorial', u'task', u'project']:
        progress = dbsession.query(UserPartProgress).\
            filter(and_(UserPartProgress.user_id == user.id,
                        UserPartProgress.part_id == part.id)).first()
        if not progress:
            progress = UserPartProgress(user_id=user.id,
                                        part_id=part.id)
    elif part.type == u'page':
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
            if part.type == u'page':
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
                                      type=u'file')
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


@view_config(route_name='part.view')
@render({'text/html': 'part/view.html'})
@current_user()
@require_logged_in()
def view_part(request):
    u"""Handles the ``parts/{pid}`` URL, displaying the
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
            return {'part': part,
                    'crumbs': crumbs,
                    'progress': progress}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


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


def create_part_crumbs(request, part, current=None):
    u"""Creates the list of breadcrumbs for a given ``part``. If the ``current`` is a ``list``,
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
        crumbs.append({'title': part.title,
                       'url': request.route_url('part.view', pid=part.id)})
        recurse_part = recurse_part.parent
    if part:
        if part.type == 'project':
            crumbs.append({'title': 'My Projects',
                           'url': request.route_url('user.projects', uid=request.current_user.id)})
        else:
            crumbs.append({'title': 'Modules',
                           'url': request.route_url('modules')})
    crumbs.reverse()
    if current:
        if isinstance(current, list):
            crumbs.extend(current)
        else:
            crumbs.append(current)
    crumbs[-1]['current'] = True
    return crumbs


@view_config(route_name='part.new')
@render({'text/html': 'part/new.html'})
@current_user()
@require_logged_in()
def new(request):
    u"""Handles the ``/parts/new`` URL, providing the UI and
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
        filter(Part.id == request.params[u'parent_id']).first()\
        if u'parent_id' in request.params else None
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
    elif request.matchdict['new_type'] == 'project':
        if not request.current_user.has_permission('projects.create'):
            raise unauthorised_redirect(request)
        elif parent:
            request.session.flash('You cannot create a new project here', queue='error')
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
                elif request.matchdict['new_type'] == 'project':
                    new_part.users.append(UserPartRole(user=request.current_user,
                                                       role=u'owner'))
                dbsession.add(new_part)
            dbsession.add(new_part)
            request.session.flash('Your new %s has been created' % (request.matchdict['new_type']), queue='info')
            if request.matchdict['new_type'] == 'project':
                raise HTTPSeeOther(request.route_url('part.view', pid=new_part.id))
            else:
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
@require_logged_in()
def edit(request):
    u"""Handles the ``/parts/{pid}/edit`` URL,
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
                    print(e)
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
@require_logged_in()
def delete(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/delete`` URL, providing
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
            if request.method == u'POST':
                part_type = part.type
                parent = part.parent
                with transaction.manager:
                    dbsession.add(part)
                    for progress in dbsession.query(UserPartProgress).filter(UserPartProgress.current_id == part.id):
                        progress.current_id = None
                    dbsession.delete(part)
                request.session.flash('The %s has been deleted' % (part_type), queue='info')
                if parent:
                    dbsession.add(parent)
                    raise HTTPSeeOther(request.route_url('part.view', pid=parent.id))
                else:
                    dbsession.add(request.current_user)
                    if part_type == 'project':
                        raise HTTPSeeOther(request.route_url('user.projects', uid=request.current_user.id))
                    else:
                        raise HTTPSeeOther(request.route_url('user.modules', uid=request.current_user.id))
            return {'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.preview')
@render({'application/json': True})
@current_user()
@require_logged_in()
def preview(request):
    u"""Handles the ``/parts/{pid}/rst_preview`` URL, generating an HTML preview of
    the submitted ReST. The ReST text to render has to be set as the ``content`` parameter.

    Requires that the user has "edit" rights on the current :class:`~wte.models.Part`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
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
@require_logged_in()
def register(request):
    u"""Handles the ``/parts/{pid}/register`` URL, to allow users to register
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
    u"""Recursively returns the :class:`~wte.models.Part` and all its children.

    :param part: The :class:`~wte.models.Part` for which to find it children
    :type part: :class:`~wte.models.Part`
    :return: The ``part`` and all its children
    :rtype: ``list``
    """
    parts = [part]
    for child in part.children:
        parts.extend(get_all_parts(child))
    return parts


@view_config(route_name='part.deregister')
@render({'text/html': 'part/deregister.html'})
@current_user()
@require_logged_in()
def deregister(request):
    u"""Handles the ``/parts/{pid}/deregister`` URL, to allow users to de-register
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
                                UserPartRole.role == u'student')).first()
                if role:
                    dbsession.delete(role)
                parts = get_all_parts(part)
                for child_part in parts:
                    progress = dbsession.query(UserPartProgress).\
                        filter(and_(UserPartProgress.part_id == child_part.id,
                                    UserPartProgress.user_id == request.current_user.id)).first()
                    if progress:
                        dbsession.delete(progress)
            request.session.flash('You have de-registered from the module', queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=request.matchdict['pid']))
        return {'part': part,
                'crumbs': crumbs}
    else:
        raise HTTPNotFound()


class ChangeStatusSchema(formencode.Schema):
    u"""The :class:`~wte.views.part.ChangeStatusSchema` handles the validation
    for editing :class:`~wte.models.Part`.
    """
    status = formencode.All(formencode.validators.UnicodeString(not_empty=True),
                            formencode.validators.OneOf([u'unavailable',
                                                         u'available']))
    u"""The part's status"""


@view_config(route_name='part.change_status')
@render({'text/html': 'part/change_status.html'})
@current_user()
@require_logged_in()
def change_status(request):
    u"""Handles the ``/parts/{pid}/change_status`` URL,
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
            if request.method == u'POST':
                try:
                    params = ChangeStatusSchema().to_python(request.params)
                    with transaction.manager:
                        dbsession.add(part)
                        part.status = params['status']
                    dbsession.add(part)
                    request.session.flash('The %s is now %s' % (part.type, part.status), queue='info')
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


@view_config(route_name='part.export')
@current_user()
@require_logged_in()
def export(request):
    u"""Handles the ``/parts/{pid}/export`` URL, providing the UI and backend
    for exporting a :class:`~wte.models.Part`.

    Requires that the user has "edit" rights on the :class:`~wte.models.Part`.
    """
    def part_as_dict(part, assets):
        data = {'type': part.type,
                'title': part.title,
                'status': part.status,
                'order': part.order,
                'content': part.content}
        if part.children:
            data['children'] = [part_as_dict(child, assets) for child in part.children]
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
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
    if part:
        if part.allow('edit', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Export',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                body = StringIO()
                body_zip = ZipFile(body, 'w')
                assets = []
                data = part_as_dict(part, assets)
                body_zip.writestr('content.json', json.dumps(data), ZIP_DEFLATED)
                for export_id, asset_id in assets:
                    asset = dbsession.query(Asset).filter(Asset.id == asset_id).first()
                    if asset:
                        if asset.mimetype.startswith('text'):
                            body_zip.writestr('assets/%s' % (export_id), asset.data, ZIP_DEFLATED)
                        else:
                            body_zip.writestr('assets/%s' % (export_id), asset.data, ZIP_STORED)
                body_zip.close()
                return Response(body=str(body.getvalue()),
                                headers=[('Content-Type', 'application/zip'),
                                         ('Content-Disposition', str('attachment; filename="%s.zip"' % (part.title)))])

            @render({'text/html': 'part/export.html'})
            def render_form(request):
                return {'part': part,
                        'crumbs': crumbs}
            return render_form(request)
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


class ImportPartConverter(formencode.FancyValidator):
    u"""The :class:`~wte.views.part.ImportPartConverter` converts a :class:`~cgi.FieldStorage`
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
        u"""Convert the submitted ``value`` into a (``dict``, :class:`~zipfile.ZipFile`)
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
            data = json.load(zip_file.open('content.json'))
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
        u"""Checks that the uploaded "content.json" file is actually valid. Checks that the
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
                if data['type'] not in ['tutorial', 'exercise']:
                    raise formencode.api.Invalid(self.message('invalidpart',
                                                              state,
                                                              part_type=data['type']),
                                                 value,
                                                 state)
            elif state.parent.type == 'tutorial':
                if data['type'] != 'page':
                    raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                                 value,
                                                 state)
            elif state.parent.type == 'exercise':
                if data['type'] != 'task':
                    raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                                 value,
                                                 state)
            else:
                raise formencode.api.Invalid(self.message('invalidpart', state, part_type=data['type']),
                                             value,
                                             state)


class ImportPartSchema(formencode.Schema):
    u"""The :class:`~wte.views.part.ImportPartSchema` validates the request to import
    a :class:`~wte.models.Part` (and any children and :class:`~wte.models.Asset`).

    Uses the :class:`~wte.views.part.ImportPartConverter` to actually check whether the
    uploaded file is a valid export generated from :func:`~wte.views.part.export`.
    """

    parent_id = formencode.validators.Int(if_missing=None)
    file = formencode.compound.Pipe(formencode.validators.FieldStorageUploadConverter(not_empty=True),
                                    ImportPartConverter())


@view_config(route_name='part.import')
@render({'text/html': 'part/import.html'})
@current_user()
@require_logged_in()
def import_file(request):
    u"""Handles the ``/parts/import`` URL, providing the UI and
    backend for importing a :class:`~wte.models.Part`.

    The required permissions depend on the type of :class:`~wte.models.Part`
    to create:
    * `module` -- User permission "modules.create"
    * `tutorial` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `page` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `exercise` -- "edit" permission on the parent :class:`~wte.models.Part`
    * `task` -- "edit" permission on the parent :class:`~wte.models.Part`
    """
    def recursive_import(data, zip_file):
        part = Part(type=data['type'],
                    title=data['title'],
                    status=u'unavailable')
        if 'order' in data:
            try:
                part.order = int(data['order'])
            except ValueError:
                part.order = 0
        if 'content' in data:
            part.content = data['content']
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
                child_part = recursive_import(child, zip_file)
                part.children.append(child_part)
                child_part.parent = part
        return part

    dbsession = DBSession()
    parent = dbsession.query(Part).\
        filter(Part.id == request.params[u'parent_id']).first()\
        if u'parent_id' in request.params else None
    if parent and not parent.allow('edit', request.current_user):
        unauthorised_redirect(request)
    elif not parent and not request.current_user.has_permission('modules.create'):
        unauthorised_redirect(request)
    crumbs = create_part_crumbs(request,
                                parent,
                                {'title': 'Import',
                                 'url': request.current_route_url()})
    if request.method == u'POST':
        try:
            params = ImportPartSchema().to_python(request.params, State(parent=parent))
            with transaction.manager:
                if parent:
                    dbsession.add(parent)
                part = recursive_import(params['file'][0], params['file'][1])
                dbsession.add(part)
                params['file'][1].close()
                if part.type == u'module':
                    part.users.append(UserPartRole(user=request.current_user,
                                                   role=u'owner'))
                if parent:
                    parent.children.append(part)
            dbsession.add(part)
            request.session.flash('Your %s has been imported' % (part.type), queue='info')
            raise HTTPSeeOther(request.route_url('part.view', pid=part.id))
        except formencode.Invalid as e:
            e.params = request.params
            return {'e': e,
                    'crumbs': crumbs}
    return {'crumbs': crumbs}
