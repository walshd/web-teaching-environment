# -*- coding: utf-8 -*-
"""
####################################
:mod:`wte.models` -- Database Models
####################################

The :mod:`~wte.models` module contains the database models that are used to
abstract the actual database.
"""
from __future__ import (unicode_literals)  # Python 2.7 compatibility

import json
import re

from datetime import datetime
from pywebtools.pyramid.auth.models import Base, User
from sqlalchemy import (Column, Index, ForeignKey, Integer, Unicode,
                        UnicodeText, Table, LargeBinary, DateTime, Boolean)
from sqlalchemy.orm import (relationship, backref)

from wte.helpers.frontend import confirm_delete, MenuBuilder, confirm_action

DB_VERSION = '1d79e6b04177'
"""The currently required database version."""


class UserPartRole(Base):
    """The :class:`~wte.models.UserPartRole` links users to :class:`~wte.models.Part`
    that have a type "module". They represent the role the :class:`~wte.models.User`
    plays for that :class:`~wte.models.Part`.

    Instances of :class:`~wte.models.UserPartRole` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``part_id`` -- The unique database identifier of the linked :class:`~wte.models.Part`
    * ``part`` -- The linked :class:`~wte.models.Part`
    * ``role`` -- The role the :class:`~wte.models.User` plays in the :class:`~wte.models.Part`
    * ``user_id`` -- The unique database identifier of the linked :class:`~wte.models.User`
    * ``user`` -- The linked :class:`~wte.models.User`
    """
    __tablename__ = 'users_parts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', name='users_parts_user_id_fk'))
    part_id = Column(Integer, ForeignKey('parts.id', name='users_parts_part_id_fk'))
    role = Column(Unicode(255))

    user = relationship(User)
    part = relationship('Part')


class Part(Base):
    """The :class:`~wte.models.Part` class represents the parts from which the teaching
    content is constructed. It supports the following types: module, tutorial, page,
    exercise, and task.

    Instances of :class:`~wte.models.Part` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``access_rights`` -- JSON structure representing the access rights to
      this :class:`~wte.models.Part`
    * ``assets`` -- List of :class:`~wte.models.Asset` that act as asset files
    * ``children`` -- List of :class:`~wte.models.Part` contained in this
      :class:`~wte.models.Part`
    * ``compiled_content`` -- The compiled HTML generated from the ReST ``content``
    * ``content`` -- The ReST content for the :class:`~wte.models.Part`
    * ``display_mode`` -- The display template mode to use for the :class:`~wte.models.Part`
    * ``label`` -- The classification label to use for the :class:`~wte.models.Part`
    * ``order`` -- The ordering position of this :class:`~wte.models.Part`
    * ``parent_id`` -- The unique database identifier of the parent :class:`~wte.models.Part`
    * ``parent`` -- The parent :class:`~wte.models.Part`
    * ``progress`` -- The :class:`~wte.models.UserPartProgress` linked to this :class:`~wte.models.Part`
    * ``status`` -- The :class:`~wte.models.Part`'s availability status
    * ``summary`` -- The shortened summary derived from the ``compiled_content``
    * ``tasks`` -- List of :class:`~wte.models.TimedTask` that are attached to this
      :class:`~wte.models.Part`
    * ``templates`` -- List of :class:`~wte.models.Asset` that act as template files
    * ``title`` -- The title displayed for this :class:`~wte.models.Part`
    * ``type`` -- Whether the :class:`~wte.models.Part` is a module, tutorial, page,
      exercise, or task.
    * ``users`` -- The :class:`~wte.models.User` that are linked to this :class:`~wte.models.Part`
    """
    __tablename__ = 'parts'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('parts.id', name='parts_parent_id_fk'))
    order = Column(Integer)
    title = Column(Unicode(255))
    status = Column(Unicode(255))
    type = Column(Unicode(255))
    display_mode = Column(Unicode(255))
    label = Column(Unicode(255), index=True)
    content = Column(UnicodeText)
    compiled_content = Column(UnicodeText)
    access_rights = Column(UnicodeText)

    children = relationship('Part',
                            backref=backref('parent', remote_side=[id]),
                            cascade='all,delete',
                            order_by='Part.order')
    templates = relationship('Asset',
                             secondary='parts_assets',
                             secondaryjoin="and_(Asset.id==parts_assets.c.asset_id, Asset.type=='template')",
                             order_by='Asset.order',
                             viewonly=True)
    assets = relationship('Asset',
                          secondary='parts_assets',
                          secondaryjoin="and_(Asset.id==parts_assets.c.asset_id, Asset.type=='asset')",
                          order_by='Asset.order',
                          viewonly=True)
    all_assets = relationship('Asset',
                              cascade='all',
                              secondary='parts_assets',
                              backref='parts')
    users = relationship('UserPartRole',
                         cascade='all')
    progress = relationship('UserPartProgress',
                            cascade='all',
                            primaryjoin='Part.id==UserPartProgress.part_id')
    tasks = relationship('TimedTask',
                         cascade='all')

    def root(self):
        """Gets the root :class:`~wte.models.Part` for the current :class:`~wte.models.Part`.
        If the :class:`~wte.models.Part` has no parent, then returns itself.

        :return: The root :class:`~wte.models.Part`
        :rtype: :class:`~wte.models.Part`
        """
        if self.parent:
            return self.parent.root()
        else:
            return self

    def allow(self, action, user):
        """Checks whether the given ``user`` is allowed to perform the given
        ``action``. Supports the following actions: view, edit, delete, and users.

        :param action: The action to check for
        :type action: `unicode`
        :param user: The user to check
        :type user: :class:`~wte.models.User`
        :return: ``True`` if the ``user`` may perform the action, ``False``
                 otherwise
        :rtype: `bool`
        """
        if not user.logged_in:
            return False
        if action == 'view':
            root = self.root()
            if user.has_permission('admin.modules.view'):
                return True
            elif root.has_role(['owner', 'tutor'], user):
                return True
            elif root.has_role('student', user):
                if self.parent:
                    if self.parent.allow(action, user) and self.status in ['available', 'archived']:
                        return True
                else:
                    if self.status in ['available', 'archived']:
                        return True
            elif self.type == 'module' and self.status == 'available':
                return True
        elif action == 'edit':
            if user.has_permission('admin.modules.edit'):
                return True
            elif self.has_role('owner', user):
                return True
            elif self.parent:
                return self.parent.allow(action, user)
        elif action == 'delete':
            if user.has_permission('admin.modules.delete'):
                return True
            elif self.has_role('owner', user):
                return True
            elif self.parent:
                return self.parent.allow(action, user)
        elif action == 'users':
            if self.type == 'module':
                if self.has_role('owner', user):
                    return True
                else:
                    return False
            elif self.parent:
                self.parent.allow(action, user)
        return False

    def has_role(self, role, user):
        """Checks if the given ``user`` has the given ``role`` for this :class:`~wte.models.Part`.
        If a ``list`` is specified as the ``role``, then the ``user`` must have at least one of the
        specified roles.

        :param role: The role the user must have.
        :type role: ``unicode`` or ``list``
        :param user: The user that has to have the role
        :type user: :class:`~wte.models.User`
        :return: ``True`` if the :class:`~wte.models.User` has the given role, ``False`` otherwise
        :rtype: ``bool``
        """
        if isinstance(role, list):
            for sub_role in role:
                if self.has_role(sub_role, user):
                    return True
        else:
            for user_role in self.users:
                if user_role.role == role and user_role.user == user:
                    return True
        if self.parent:
            return self.parent.has_role(role, user)
        return False

    def register_state(self, user):
        if self.has_role(['student', 'owner'], user):
            return 'already_registered'
        if self.access_rights:
            rights = json.loads(self.access_rights)
            if rights:
                if 'password' in rights and 'email_domains' in rights:
                    if user.email[user.email.find('@') + 1:] in rights['email_domains']:
                        return 'password_register'
                    else:
                        return 'invalid_email_domain'
                elif 'password' in rights:
                    return 'password_register'
                elif 'email_domains' in rights:
                    if user.email[user.email.find('@') + 1:] in rights['email_domains']:
                        return 'plain_register'
                    else:
                        return 'invalid_email_domain'
        return 'plain_register'

    @property
    def summary(self):
        """Generates the text summary for this :class:`~wte.models.Part`.
        The text summary is generated by finding the first tag in the ``compiled_content``
        and then returning that.

        :return: The content of the first tag in the ``compiled_content``
        :r_type: :class:`unicode`
        """
        if self.compiled_content:
            match = re.search(r'<([a-zA-Z+])>', self.compiled_content)
            if match:
                start = self.compiled_content.find('<%s>' % (match.group(1)))
                end = self.compiled_content.find('</%s>' % (match.group(1))) + len(match.group(1)) + 3
                return self.compiled_content[start:end]
        return None

    @property
    def available_children(self):
        """Returns the list of child :class:`~wte.models.Part` for which the ``status``
        attribute is set to "available".

        :return: The available child :class:`~wte.models.Part`
        :rtype: :func:`list`
        """
        if not hasattr(self, '_available_children'):
            self._available_children = [p for p in self.children if p.status == 'available']
        return self._available_children

    @property
    def prev(self):
        """Returns the previous :class:`~wte.models.Part` in the list of siblings.

        :return: The previous :class:`~wte.models.Part` sibling
        :rtype: :class:`~wte.models.Part`
        """
        prev = None
        for child in self.parent.children:
            if child.id == self.id:
                return prev
            if child.status == 'available':
                prev = child

    @property
    def next(self):
        """Returns the next :class:`~wte.models.Part` in the list of siblings.

        :return: The next :class:`~wte.models.Part` sibling
        :rtype: :class:`~wte.models.Part`
        """
        found = False
        for child in self.parent.children:
            if found and child.status == 'available':
                return child
            if child.id == self.id:
                found = True
        return None

    def menu(self, request):
        """Generates the menu for the :class:`~wte.models.Part`.
        """
        builder = MenuBuilder()
        builder.group('Status', 'fi-lock' if self.status == 'available' else 'fi-unlock')
        if self.allow('edit', request.current_user):
            # Status Change Items
            if self.status == 'available':
                builder.menu('Make unavailable',
                             request.route_url('part.change_status',
                                               pid=self.id,
                                               _query=[('status', 'unavailable'),
                                                       ('return_to', request.current_route_url()),
                                                       ('csrf_token', request.session.get_csrf_token())]),
                             icon='fi-lock',
                             highlight=True,
                             attrs={'class': 'post-link'})
            else:
                builder.menu('Make available',
                             request.route_url('part.change_status',
                                               pid=self.id,
                                               _query=[('status', 'available'),
                                                       ('return_to', request.current_route_url()),
                                                       ('csrf_token', request.session.get_csrf_token())]),
                             icon='fi-unlock',
                             highlight=True,
                             attrs={'class': 'post-link'})
            # Archive Menu Item
            if self.type == 'module' and self.status != 'archived':
                builder.menu('Archive',
                             request.route_url('part.change_status',
                                               pid=self.id,
                                               _query=[('status', 'archived'),
                                                       ('return_to', request.current_route_url()),
                                                       ('csrf_token', request.session.get_csrf_token())]),
                             attrs={'class': 'post-link'})
            builder.group('Edit', 'fi-pencil')
            # Edit Menu Item
            builder.menu('Edit',
                         request.route_url('part.edit', pid=self.id),
                         icon='fi-pencil',
                         highlight=True)
            # Edit Timed Actions Menu
            builder.menu('Edit Timed Actions',
                         request.route_url('part.timed_task', pid=self.id),
                         icon='fi-clock')
            builder.group('Users')
            if self.type == 'module':
                # User Menu Item
                builder.menu('Users',
                             request.route_url('part.users', pid=self.id),
                             icon='fi-torsos-all')
                # Access Settings Menu Item
                if self.status != 'archived':
                    builder.menu('Edit Access Settings',
                                 request.route_url('part.register.settings', pid=self.id),
                                 icon='fi-key')
            builder.group('add', 'fi-plus')
            if self.type == 'module':
                # Add Part Menu Item
                builder.menu('Add Part',
                             request.route_url('part.new', new_type='part', _query=[('parent_id', self.id)]),
                             icon='fi-plus',
                             highlight=True)
            if self.type == 'part':
                builder.menu('Add Page',
                             request.route_url('part.new', new_type='page', _query=[('parent_id', self.id)]),
                             icon='fi-plus',
                             highlight=True)
                builder.menu('Add Template',
                             request.route_url('asset.new', pid=self.id, new_type='template'),
                             highlight=True)
            if self.type == 'page':
                # Add page bfore / after Menu Item
                builder.menu('Add Page before',
                             request.route_url('part.new',
                                               new_type='page',
                                               _query=[('parent_id', self.parent.id),
                                                       ('order', self.order)]),
                             highlight=True)
                builder.menu('Add Page after',
                             request.route_url('part.new',
                                               new_type='page',
                                               _query=[('parent_id', self.parent.id),
                                                       ('order', self.order + 1)]),
                             highlight=True)
            # Add Asset Menu Item
            builder.menu('Add Asset',
                         request.route_url('asset.new', pid=self.id, new_type='asset'))
        builder.group('Import / Export')
        if self.allow('edit', request.current_user):
            if self.type in ['module', 'part']:
                # Import Menu Item
                builder.menu('Import',
                             request.route_url('part.import', _query=[('parent_id', self.id)]))
            # Export Menu Item
            builder.menu('Export',
                         request.route_url('part.export',
                                           pid=self.id,
                                           _query=[('csrf_token', request.session.get_csrf_token())]),
                         attrs={'class': 'post-link'})
        if self.allow('view', request.current_user):
            # Download Menu Item
            builder.menu('Download',
                         request.route_url('part.download', pid=self.id),
                         attrs={'class': 'post-link'})
        if self.allow('delete', request.current_user):
            builder.group('Delete')
            # Delete Menu Item
            builder.menu('Delete',
                         request.route_url('part.delete',
                                           pid=self.id,
                                           _query=[('csrf_token', request.session.get_csrf_token())]),
                         icon='fi-trash',
                         attrs={'class': 'alert post-link',
                                'data-wte-confirm': confirm_delete(self.type, self.title, True)})
        return builder.generate()


Index('parts_parent_id_ix', Part.parent_id)


class UserPartProgress(Base):
    """The :class:`~wte.models.UserPartProgress` represents the progress a
    :class:`~wte.models.User` has made through a :class:`~wte.models.Part`.

    Instances of :class:`~wte.models.UserPartProgress` have the following
    attributes:

    * ``id`` -- The unique database identifier
    * ``current_id`` -- The unique database identifier of the current :class:`~wte.models.Part`
    * ``current`` -- The current :class:`~wte.models.Part`
    * ``files`` -- The :class:`~wte.models.Asset` that are linked to this :class:`~wte.models.UserPartProgress`
    * ``part_id`` -- The unique identifier of the :class:`~wte.models.Part`
    * ``part`` -- The :class:`~wte.models.Part` that this represents the
      progress in
    * ``user_id`` -- The unique identifier of the :class:`~wte.models.User`
    * ``user`` -- The :class:`~wte.models.User` for which this represents the
      progress
    """

    __tablename__ = 'user_part_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, name='user_part_progress_user_id_fk'))
    part_id = Column(Integer, ForeignKey(Part.id, name='user_part_progress_part_id_fk'))
    current_id = Column(Integer, ForeignKey(Part.id, name='user_part_progress_current_id_fk'))

    user = relationship('User')
    part = relationship('Part', foreign_keys=[part_id])
    current = relationship('Part', foreign_keys=[current_id])
    files = relationship('Asset',
                         cascade="all",
                         secondary='progress_assets',
                         order_by='Asset.order')

    def allow(self, action, user):
        """Checks whether the given ``user`` is allowed to perform the given
        ``action``. Supports the following action: view.

        :param action: The action to check for
        :type action: `unicode`
        :param user: The user to check
        :type user: :class:`~wte.models.User`
        :return: ``True`` if the ``user`` may perform the action, ``False``
                 otherwise
        :rtype: `bool`
        """
        if user.id == self.user_id:
            return True
        return False

Index('user_part_progress_user_id_ix', UserPartProgress.user_id)
Index('user_part_progress_part_id_ix', UserPartProgress.part_id)
Index('user_part_progress_user_id_part_id_ix', UserPartProgress.user_id, UserPartProgress.part_id)


class Asset(Base):
    """The class:`~wte.models.Asset` represents any kind of file data. What role the
    :class:`~wte.models.Asset` is used in depends on the ``type``.

    Instances of :class:`~wte.models.Asset` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``data`` -- The actual file content
    * ``filename`` -- The filename used for accessing this :class:`~wte.models.Asset`
    * ``mimetype`` -- The mimetype of this :class:`~wte.models.Asset`
    * ``order`` -- The order to display this :class:`~wte.models.Asset` in
    * ``parts`` -- The :class:`~wte.models.Part` that this :class:`~wte.models.Asset` is used in
    * ``type`` -- The type of :class:`~wte.models.Asset` it is (asset, template, file)
    """

    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True)
    type = Column(Unicode(255))
    filename = Column(Unicode(255))
    mimetype = Column(Unicode(255))
    order = Column(Integer)
    data = Column(LargeBinary)
    etag = Column(Unicode(255))

    def menu(self, request, part=None):
        """Generate the menu for this :class:`~wte.models.Asset`. Will distinguish between
        assets, templates, and files.
        """
        builder = MenuBuilder()
        if self.type in ['asset', 'template'] and part is not None:
            if part.allow('edit', request.current_user):
                builder.group('Edit',
                              icon='fi-pencil')
                builder.menu('Edit',
                             request.route_url('asset.edit', pid=part.id, aid=self.id),
                             icon='fi-pencil',
                             highlight=True)
                builder.group('Delete')
                builder.menu('Delete',
                             request.route_url('asset.delete',
                                               pid=part.id,
                                               aid=self.id,
                                               _query=[('csrf_token', request.session.get_csrf_token())]),
                             icon='fi-trash',
                             attrs={'class': 'alert post-link',
                                    'data-wte-confirm': confirm_delete('asset', self.filename, False)})
        elif self.type == 'file':
            builder.group('Save',
                          icon='fi-save')
            builder.menu('Save',
                         '#',
                         icon='fi-save',
                         highlight=True,
                         attrs={'class': 'save'})
            builder.menu('Download',
                         request.route_url('file.view',
                                           pid=part.id,
                                           filename=self.filename,
                                           _query=[('download', 'true')]))
            builder.group('Delete')
            builder.menu('Discard Changes',
                         request.route_url('part.reset-files',
                                           pid=part.id,
                                           _query={'filename': self.filename,
                                                   'csrf_token': request.session.get_csrf_token()}),
                         attrs={'class': 'alert post-link',
                                'data-wte-confirm': confirm_action('Discard Changes',
                                                                   'Please confirm that you wish to discard the ' +
                                                                   'changes you made to the file ' +
                                                                   '"%s" and reset it ' % (self.filename) +
                                                                   'to its initial content.',
                                                                   "Don't Discard",
                                                                   {'label': 'Discard',
                                                                    'class_': 'alert'})})
        return builder.generate()


Index('assets_filename_ix', Asset.filename)
Index('assets_type_ix', Asset.type)


parts_assets = Table('parts_assets', Base.metadata,
                     Column('part_id',
                            ForeignKey('parts.id',
                                       name='parts_assets_part_id_fk'),
                            primary_key=True),
                     Column('asset_id',
                            ForeignKey('assets.id',
                                       name='parts_assets_asset_id_fk'),
                            primary_key=True))
""":class:`sqlalchemy.Table` to link :class:`~wte.models.Part` and
:class:`~wte.models.Asset`.
"""

progress_assets = Table('progress_assets', Base.metadata,
                        Column('progress_id',
                               ForeignKey('user_part_progress.id',
                                          name='progress_assets_progress_id_fk'),
                               primary_key=True),
                        Column('asset_id',
                               ForeignKey('assets.id',
                                          name='parts_assets_asset_id_fk'),
                               primary_key=True))
""":class:`sqlalchemy.Table` to link :class:`~wte.models.Part` and
:class:`~wte.models.Asset`.
"""


class TimedTask(Base):
    """The class:`~wte.models.TimedTask` represents a task that is to be run at a specific
    time in the future.

    Instances of :class:`~wte.models.TimedTask` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``part_id`` -- The unique identifier of the :class:`~wte.models.Part` the
      :class:`~wte.models.TimedTask` belongs to
    * ``name`` -- The name of this :class:`~wte.models.TimedTask`
    * ``title`` -- The title of this :class:`~wte.models.TimedTask`
    * ``timestamp`` -- The timestamp at which to execute this :class:`~wte.models.TimedTask`
    * ``_options`` -- The task options as JSON (do not use directly, use
      :attr:`~wte.models.TimedTask.options`)
    """

    __tablename__ = 'timed_tasks'

    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey('parts.id',
                                         name='timed_tasks_part_id_fk'))
    name = Column(Unicode(255))
    title = Column(Unicode(255))
    timestamp = Column(DateTime, index=True)
    _options = Column(UnicodeText)
    status = Column(Unicode(255))

    __table_args__ = (Index('ix_timed_tasks_timestamp_status', 'timestamp', 'status'), )

    def _get_options(self):
        """Get / Set the options for this :class:`~wte.models.TimedTask`.

        When setting options, the new options must be of type ``dict``.

        When getting options, the options will be returned as a ``dict``.
        """
        if not hasattr(self, '_options_cache'):
            if self._options:
                self._options_cache = json.loads(self._options)
            else:
                self._options_cache = {}
        return self._options_cache

    def _set_options(self, options):
        if hasattr(self, '_options_cache'):
            del self._options_cache
        if isinstance(options, dict):
            self._options = json.dumps(options)
        else:
            self._options = json.dumps({})

    options = property(_get_options, _set_options)

    def _get_delta(self):
        """Get the ``timedelta`` between the :class:`~wte.models.TimedTask`\'s
        ``timestamp`` and ``datetime.now()``."""
        return self.timestamp - datetime.now()

    delta = property(_get_delta)

    def menu(self, request, part):
        """Generate the menu for this :class:`~wte.models.TimedTask`.
        """
        builder = MenuBuilder()
        builder.group('Edit',
                      icon='fi-pencil')
        builder.menu('Edit',
                     request.route_url('part.timed_task.edit', pid=part.id, tid=self.id),
                     icon='fi-pencil',
                     highlight=True)
        builder.group('Delete')
        builder.menu('Delete',
                     request.route_url('part.timed_task.delete',
                                       pid=part.id,
                                       tid=self.id,
                                       _query={'csrf_token': request.session.get_csrf_token()}),
                     icon='fi-trash',
                     attrs={'class': 'alert post-link',
                            'data-wte-confirm': confirm_delete('timed action',
                                                               self.title,
                                                               False)})
        return builder.generate()


class Quiz(Base):
    """The :class:`~wte.models.Quiz` represents a :class:`~wte.text_formatter.docutils_ext.Quiz`
    in the database.

    Instances of :class:`~wte.models.QuizAnswer` have the following attributes:

    * ``id`` - The unique database identifier
    * ``answers`` - All :class:`~wte.models.QuizAnswer` that belong to this :class:`~wte.models.Quiz`
    * ``part_id`` - The unique identifier of the :class:`~wte.models.User` the
      :class:`~wte.models.Part` belongs to
    * ``name`` - The name of the :class:`~wte.text_formatter.docutils_ext.Quiz`.
    """

    __tablename__ = 'quizzes'

    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey('parts.id',
                                         name='quiz_answers_part_id_fk'))
    name = Column(Unicode(255))

    answers = relationship('QuizAnswer')


Index('quizzes_full_ix', Quiz.part_id, Quiz.name)


class QuizAnswer(Base):
    """The class:`~wte.models.QuizAnswer` represents an answer to a
    :class:`~wte.text_formatter.docutils_ext.QuizQuestion` in a
    :class:`~wte.models.Quiz`. 

    Instances of :class:`~wte.models.QuizAnswer` have the following attributes:

    * ``id`` - The unique database identifier
    * ``attempts`` - How many attempts the user has had
    * ``final_answer`` - The final answer the user provided
    * ``final_correct`` - Whether the final answer was correct
    * ``initial_answer`` - The first answer the user provided
    * ``initial_correct`` - Whether the first answer was correct
    * ``question`` - The name of the :class:`~wte.text_formatter.docutils_ext.QuizQuestion`.
    * ``quiz_id`` - The unique identifier of the :class:`~wte.models.Quiz` the
      :class:`~wte.models.QuizAnswer` belongs to
    * ``quiz`` - The :class:`~wte.models.Quiz` identified by ``quiz_id``
    * ``user_id`` - The unique identifier of the :class:`~wte.models.User` the
      :class:`~wte.models.QuizAnswer` belongs to
    """
    
    __tablename__ = 'quiz_answers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id',
                                         name='quiz_answers_user_id_fk'))
    quiz_id = Column(Integer, ForeignKey('quizzes.id',
                                         name='quiz_answers_quiz_id_fk'))
    question = Column(Unicode(255))
    initial_answer = Column(Unicode(255))
    initial_correct = Column(Boolean)
    final_answer = Column(Unicode(255))
    final_correct = Column(Boolean)
    attempts = Column(Integer)

    quiz = relationship('Quiz')


Index('quiz_answers_full_ix', QuizAnswer.user_id, QuizAnswer.quiz_id, QuizAnswer.question)
