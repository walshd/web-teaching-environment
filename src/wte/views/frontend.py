# -*- coding: utf-8 -*-
u"""
###################################################
:mod:`wte.views.frontend` -- Frontend view handlers
###################################################

The :mod:`~wte.views.frontend` handles the frontend functionality for
interacting with :class:`~wte.models.Module`, :class:`~wte.models.Part`, and
:class:`~wte.models.Page`.

Routes are defined in :func:`~wte.views.frontend.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import transaction

from pyramid.httpexceptions import (HTTPNotFound, HTTPSeeOther)
from pyramid.response import Response
from pyramid.view import view_config
from pywebtools.renderer import render
from sqlalchemy import and_
from StringIO import StringIO
from zipfile import ZipFile

from wte.decorators import current_user
from wte.models import (DBSession, Part, User, UserPartProgress,
                        Asset, UserPartRole)
from wte.util import (unauthorised_redirect)
from wte.views.part import create_part_crumbs


def init(config):
    u"""Adds the frontend-specific backend routes (route name, URL pattern
    handler):
    
    * ``modules`` -- ``/modules`` -- :func:`~wte.views.frontend.modules`
    * ``module.view`` -- ``/modules/{mid}`` --
      :func:`~wte.views.frontend.view_module`
    * ``part.view`` -- ``/modules/{mid}/parts/{pid}`` --
      :func:`~wte.views.frontend.view_part`
    * ``user.modules`` -- ``/users/{uid}/modules`` --
      :func:`~wte.views.frontend.user_modules`
    * ``asset.view`` -- ``/modules/{mid}/parts/{pid}/files/name/assets/{filename}``
      -- :func:`~wte.views.frontend.view_asset`
    * ``file.view`` -- ``/modules/{mid}/parts/{pid}/files/name/{filename}``
      -- :func:`~wte.views.frontend.view_file`
    * ``file.save`` -- ``/modules/{mid}/parts/{pid}/files/id/{fid}/save``
      -- :func:`~wte.views.frontend.save_file`
    * ``part.reset-files`` -- ``/modules/{mid}/parts/{pid}/reset_files`` --
      :func:`~wte.views.part.reset_files`
    * ``userpartprogress.download`` -- ``/users/{uid}/progress/{pid}/download``
      -- :func:`~wte.views.frontend.download_part_progress`
    """
    config.add_route('modules', '/modules')
    config.add_route('module.view', '/modules/{mid}')
    config.add_route('part.view', '/parts/{pid}')
    config.add_route('user.modules', '/users/{uid}/modules')
    config.add_route('asset.view', '/parts/{pid}/files/name/assets/{filename}')
    config.add_route('file.view', '/parts/{pid}/files/name/{filename}')
    config.add_route('file.save', '/parts/{pid}/files/id/{fid}/save')
    config.add_route('part.reset-files', '/parts/{pid}/reset_files')
    config.add_route('userpartprogress.download', '/users/{uid}/progress/{pid}/download')


@view_config(route_name='modules')
@render({'text/html': 'part/list.html'})
@current_user()
def modules(request):
    u"""Handles the ``/modules`` URL, displaying all available
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    modules = dbsession.query(Part).filter(and_(Part.type==u'module',
                                                Part.status==u'available')).all()
    return {'modules': modules,
            'crumbs': [{'title': 'Modules', 'url': request.route_url('modules'), 'current': True}]}


@view_config(route_name='user.modules')
@render({'text/html': 'part/list.html'})
@current_user()
def user_modules(request):
    u"""Handles the ``/users/{uid}/modules`` URL, displaying all the
    :class:`~wte.models.Module` of the :class:`~wte.models.User`.
    
    Requires that the current user has "view" rights for the
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    user = dbsession.query(User).filter(User.id==request.matchdict['uid']).first()
    if user:
        if user.allow('view', request.current_user):
            modules = dbsession.query(Part).join(UserPartRole).filter(and_(Part.type == u'module',
                                                                           UserPartRole.user_id == request.matchdict[u'uid']))
            return {'user': user,
                    'modules': modules,
                    'crumbs': [{'title': user.display_name, 'url': request.route_url('user.view', uid=user.id)},
                               {'title': 'Modules', 'url': request.route_url('modules'), 'current': True}]}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


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
    if part.type in [u'tutorial', u'task']:
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
def view_part(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}`` URL, displaying the
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


@view_config(route_name='file.view')
@current_user()
def view_file(request):
    u"""Handles the ``/modules/{mid}/parts/{ptid}/pages/{pid}/users/{uid}/files/name/{filename}``
    URL, sending back the correct :class:`~wte.models.File`.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.Module`. It will also only send a
    :class:`~wte.models.File` belonging to the current
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict[u'pid']).first()
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            for user_file in progress.files:
                if user_file.filename == request.matchdict['filename']:
                    headers = [('Content-Type', str(user_file.mimetype))]
                    if 'download' in request.params:
                        headers.append(('Content-Disposition',
                                        str('attachment; filename="%s"' % (user_file.filename))))
                    return Response(body=user_file.data,
                                    headerlist=headers)
            raise HTTPNotFound()
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='file.save')
@render({'application/json': True})
@current_user()
def save_file(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/files/id/{fid}/save``
    URL, updating the :class:`~wte.models.File` content.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.Module`. It will also only update a
    :class:`~wte.models.File` belonging to the current
    :class:`~wte.models.User`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict[u'pid']).first()
    if part:
        if part.allow('view', request.current_user):
            progress = get_user_part_progress(dbsession, request.current_user, part)
            for user_file in progress.files:
                if user_file.id == int(request.matchdict['fid']):
                    if 'content' in request.params:
                        with transaction.manager:
                            dbsession.add(user_file)
                            user_file.data = request.params['content'].encode('utf-8')
                        return {'status': 'saved'}
                    else:
                        return {'status': 'no-changes'}
            raise HTTPNotFound()
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='part.reset-files')
@render({'text/html': 'part/reset_files.html'})
@current_user()
def reset_files(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/reset_files`` URL, providing
    the UI and backend for resetting all :class:`~wte.models.File` of a
    :class:`~wte.models.Part`
    
    Requires that the user has "edit" rights on the current
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict['pid']).first()
    if part:
        if part.allow('view', request.current_user):
            crumbs = create_part_crumbs(request,
                                        part,
                                        {'title': 'Discard all Changes',
                                         'url': request.current_route_url()})
            if request.method == u'POST':
                with transaction.manager:
                    progress = get_user_part_progress(dbsession, request.current_user, part)
                    for user_file in progress.files:
                        if 'filename' not in request.params\
                                or request.params['filename'] == user_file.filename:
                            progress.files.remove(user_file)
                            dbsession.delete(user_file)
                raise HTTPSeeOther(request.route_url('part.view',
                                                     pid=request.matchdict['pid']))
            return {'part': part,
                    'crumbs': crumbs}
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()


@view_config(route_name='asset.view')
@current_user()
def view_asset(request):
    u"""Handles the ``/modules/{mid}/parts/{pid}/files/assets/{filename}``
    URL, sending back the correct :class:`~wte.models.Asset`.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.Module`.
    """
    dbsession = DBSession()
    part = dbsession.query(Part).filter(Part.id==request.matchdict[u'pid']).first()
    if part.type == u'page':
        part = part.parent
    asset = dbsession.query(Asset).filter(Asset.filename==request.matchdict[u'filename']).first()
    if part and asset and part in asset.parts:
        if part.allow('view', request.current_user):
            return Response(body=asset.data,
                            headerlist=[('Content-Type', str(asset.mimetype))])
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()

@view_config(route_name='userpartprogress.download')
@current_user()
def download_part_progress(request):
    u"""Handles the ``/users/{uid}/progress/{pid}/download``
    URL, sending back the complete project associated with the
    :class:`~wte.models.UserPartProgress`.
    
    Requires that the user has "view" rights on the
    :class:`~wte.models.UserPartProgress`.
    """
    dbsession = DBSession()
    progress = dbsession.query(UserPartProgress).\
        filter(UserPartProgress.id == request.matchdict['pid']).first()
    if progress:
        if progress.allow('view', request.current_user):
            if progress.part.type == u'tutorial':
                basepath = '%s/%s/' % (progress.part.module.title,
                                       progress.part.title)
                filename = '%s - %s.zip' % (progress.part.module.title, progress.part.title)
            elif progress.part.type == u'task':
                basepath = '%s/%s/%s/' % (progress.part.module.title,
                                          progress.part.parent.title,
                                          progress.part.title)
                filename = '%s - %s.zip' % (progress.part.parent.title, progress.part.title)
            body = StringIO()
            zipfile = ZipFile(body, mode='w')
            for user_file in progress.files:
                zipfile.writestr('%s%s' % (basepath, user_file.filename), user_file.content.encode('utf8'))
            for asset in progress.part.assets:
                zipfile.writestr('%s/assets/%s' % (basepath, asset.filename), asset.data)
            zipfile.close()
            return Response(body=body.getvalue(),
                            headerlist=[('Content-Type', 'application/zip'),
                                        ('Content-Disposition', str('attachment; filename="%s"' % (filename)))])
        else:
            unauthorised_redirect(request)
    else:
        raise HTTPNotFound()
