# -*- coding: utf-8 -*-
u"""
####################################
:mod:`wte.models` -- Database Models
####################################

The :mod:`~wte.models` module contains the database models that are used to
abstract the actual database.

Additionally it provides the :func:`~wte.models.check_database_version`
function, which compares the current Alembic version of the database to the
required :data:`~wte.models.DB_VERSION` to ensure that the application does
not run on an outdated database schema.
"""
import json
import random
import hashlib

from datetime import datetime
from sqlalchemy import (Column, Index, ForeignKey, Integer, Unicode,
                        UnicodeText, Table, LargeBinary, DateTime)
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship,
                            reconstructor, backref)
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

DB_VERSION = u'9ca3f8c12ed'
"""The currently required database version."""


class DBUpgradeException(Exception):
    """The :class:`~wte.models.DBUpgradeException` is used to indicate that
    the database requires an upgrade before the Web Teaching Environment system
    can be used.
    """
    def __init__(self, current, required):
        self.current = current
        self.required = required

    def __repr__(self):
        return "DBUpgradeException('%s', '%s'" % (self.current, self.required)

    def __str__(self):
        return """A database upgrade is required.

You are currently running version '%s', but version '%s' is required. Please run
alembic -c config.ini upgrade to upgrade the database and then start the application
again.
""" % (self.current, self.required)


def check_database_version():
    """Checks that the current version of the database matches the version specified
    by :data:`~wte.models.DB_VERSION`.
    """
    dbsession = DBSession()
    try:
        inspector = Inspector.from_engine(dbsession.bind)
        if 'alembic_version' in inspector.get_table_names():
            result = dbsession.query('version_num').\
                from_statement('SELECT version_num FROM alembic_version WHERE version_num = :version_num').\
                params(version_num=DB_VERSION).first()
            if not result:
                result = dbsession.query('version_num').\
                    from_statement('SELECT version_num FROM alembic_version').first()
                raise DBUpgradeException(result[0], DB_VERSION)
    except OperationalError:
        raise DBUpgradeException('no version-information found', DB_VERSION)


class User(Base):
    u"""The :class:`~wte.models.User` represents a users in the WTE. Which
    functionality they can access is determined purely through the individual
    :class:`~wte.models.User`'s :class:`~wte.models.Permission`.

    Instances of the :class:`~wte.models.User` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``display_name`` -- The name to display
    * ``email`` -- The e-mail address used for login and communication
    * ``login_limit`` -- Login limitation counter to stop brute-force login
      attacks
    * ``parts`` -- The :class:`~wte.models.UserPartProgress` belonging to this
      :class:`~wte.modes.User`
    * ``password`` -- The hashed password
    * ``permissions`` -- The :class:`~wte.models.User`'s list of
      :class:`~wte.models.Permission`.
    * ``permission_groups`` -- The :class:`~wte.models.User`'s list of
      :class:`~wte.models.PermissionGroup`.
    * ``salt`` -- The password hash salt
    * ``validation_token`` -- The validation token for new users
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(Unicode(255), unique=True)
    salt = Column(Unicode(255))
    password = Column(Unicode(255))
    display_name = Column(Unicode(64))
    login_limit = Column(Integer)
    validation_token = Column(Unicode(255))

    permissions = relationship('Permission', backref='users', secondary='users_permissions')
    permission_groups = relationship('PermissionGroup', backref='users', secondary='users_permission_groups')
    parts = relationship('UserPartProgress', cascade=u'all')

    def __init__(self, email, display_name, password=None):
        u"""Constructs a new :class:`~wte.models.User` with the given email
        address, display name, and optionally password.

        :param email: The e-mail address to use
        :type email: `unicode`
        :param display_name: The name to display
        :type display_name: `unicode`
        :param password: The optional password to set
        :type password: `unicode`
        """
        self.email = email
        self.display_name = display_name
        if password:
            self.new_password(password)
        else:
            self.new_salt()
            self.password = u''
        self.login_limit = 0
        self.preferences_ = {}

    @reconstructor
    def init(self):
        self.preferences_ = {}

    def new_salt(self):
        """Generates a new :data:`~wte.models.User.salt``. Will use
        ``os.urandom`` if available and the standard pseudo-random if not.
        """
        try:
            rng = random.SystemRandom()
            self.salt = u''.join(unichr(rng.randint(32, 127)) for _ in range(32))
        except:
            self.salt = u''.join(unichr(random.randint(32, 127)) for _ in range(32))

    def new_password(self, password):
        """Sets the given ``password`` as the :class:`~wte.models.User`'s new
        password. Calls :func:`~wte.models.User.new_salt` to generate a new
        salt for the password.

        :param password: The new cleartext password
        :type password: `unicode`
        """
        self.new_salt()
        self.password = unicode(hashlib.sha512('%s$$%s' % (self.salt, password)).hexdigest())

    def random_password(self):
        """Generates a random password, 12 characters in length consisting of
        lower-case characters, upper-case characters, and numbers.

        :return: The new password
        :rtype: `unicode`
        """
        password = []
        for _ in range(0, 12):
            choice = random.randint(0, 2)
            if choice == 0:
                password.append(unichr(random.randint(48, 57)))
            elif choice == 1:
                password.append(unichr(random.randint(65, 90)))
            elif choice == 2:
                password.append(unichr(random.randint(97, 122)))
        password = u''.join(password)
        self.new_password(password)
        return password

    def password_matches(self, password):
        """Checks whether the given password matches the hashed, stored
        password.

        :param password: The password to check
        :type password: `unicode`
        :return: ``True`` if the passwords match, ``False`` otherwise
        :rtype: `bool`
        """
        password = unicode(hashlib.sha512('%s$$%s' % (self.salt, password)).hexdigest())
        return password == self.password

    def has_permission(self, permission):
        """Checks whether the user has been granted the given ``permission``,
        either directly or via a :class:`~wte.models.PermissionGroup`.

        :param permission: The permission to check for
        :type permission: `unicode`
        :return: ``True`` if the user has the permission, ``False`` otherwise
        :rtype: `bool`
        """
        dbsession = DBSession()
        direct_perm = dbsession.query(Permission.name).join(User, Permission.users).filter(User.id == self.id)
        group_perm = dbsession.query(Permission.name).join(PermissionGroup, Permission.permission_groups).\
            join(User, PermissionGroup.users).filter(User.id == self.id)
        return permission in map(lambda p: p[0], direct_perm.union(group_perm))

    def allow(self, action, user):
        """Checks whether the given ``user`` is allowed to perform the given
        ``action``. Supports the following actions: view, edit, delete.

        :param action: The action to check for
        :type action: `unicode`
        :param user: The user to check
        :type user: :class:`~wte.models.User`
        :return: ``True`` if the ``user`` may perform the action, ``False``
                 otherwise
        :rtype: `bool`
        """
        if self.id == user.id:
            return True
        elif action == 'view':
            return True  # TODO: Add support for showing / hiding profile
        elif action == 'edit':
            return user.has_permission('admin.users.edit')
        elif action == 'delete':
            return user.has_permission('admin.users.delete')
        return False

Index('users_email_ix', User.email)


users_permissions = Table('users_permissions', Base.metadata,
                          Column('user_id',
                                 ForeignKey('users.id',
                                            name='users_permissions_users_fk'),
                                 primary_key=True),
                          Column('permission_id',
                                 ForeignKey('permissions.id',
                                            name='users_permissions_permissions_fk'),
                                 primary_key=True))
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.User` and
:class:`~wte.models.Permission`.
"""


class Permission(Base):
    u"""The :class:`~wte.models.Permission` class represents a single
    permission that can be granted to a :class:`~wte.models.User` or to a
    :class:`~wte.models.PermissionGroup`.

    Instances of :class:`~wte.models.Permission` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``name`` -- The unique name used for permission checking
    * ``permission_groups`` -- List of :class:`~wte.models.PermissionGroup`
      that contain this :class:`~wte.models.Permission`
    * ``title`` -- The title displayed for this :class:`~wte.models.Permission`
    * ``users`` -- List of :class:`~wte.models.User` that have this
      :class:`~wte.models.Permission`
    """

    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), unique=True)
    title = Column(Unicode(255))

Index('permissions_name_ix', Permission.name)


class PermissionGroup(Base):
    u"""The :class:`~wte.models.PermissionGroup` groups together one or more
    :class:`~wte.models.Permission` for easier administration.

    Instances of :class:`~wte.models.PermissionGroup` have the following
    attributes:

    * ``id`` -- The unique database identifier
    * ``permissions`` -- The list of grouped :class:`~wte.models.Permission`
    * ``title`` -- The title displayed for this
      :class:`~wte.models.PermissionGroup`
    * ``users`` -- List of :class:`~wte.models.User` that have this
      :class:`~wte.models.PermissionGroup`
    """
    __tablename__ = 'permission_groups'

    id = Column(Integer, primary_key=True)
    title = Column(Unicode(255))

    permissions = relationship('Permission', backref='permission_groups', secondary='permission_groups_permissions')


groups_permissions = Table('permission_groups_permissions', Base.metadata,
                           Column('permission_group_id',
                                  ForeignKey(PermissionGroup.id,
                                             name='permission_groups_permissions_groups_fk'),
                                  primary_key=True),
                           Column('permission_id',
                                  ForeignKey(Permission.id,
                                             name='permission_groups_permissions_permissions_fk'),
                                  primary_key=True))
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.PermissionGroup` and
:class:`~wte.models.Permission`.
"""


users_groups = Table('users_permission_groups', Base.metadata,
                     Column('user_id', ForeignKey(User.id,
                                                  name='users_permission_groups_users_fk'),
                            primary_key=True),
                     Column('permission_group_id', ForeignKey(PermissionGroup.id,
                                                              name='users_permission_groups_groups_fk'),
                            primary_key=True))
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.User` and
:class:`~wte.models.PermissionGroup`.
"""


class UserPartRole(Base):
    u"""The :class:`~wte.models.UserPartRole` links users to :class:`~wte.models.Part`
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
    __tablename__ = u'users_parts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, name=u'users_parts_user_id_fk'))
    part_id = Column(Integer, ForeignKey('parts.id', name=u'users_parts_part_id_fk'))
    role = Column(Unicode(255))

    user = relationship(User)
    part = relationship(u'Part')


class Part(Base):
    u"""The :class:`~wte.models.Part` class represents the parts from which the teaching
    content is constructed. It supports the following types: module, tutorial, page,
    exercise, and task.

    Instances of :class:`~wte.models.Part` have the following attributes:

    * ``id`` -- The unique database identifier
    * ``assets`` -- List of :class:`~wte.models.Asset` that act as asset files
    * ``children`` -- List of :class:`~wte.models.Part` contained in this
      :class:`~wte.models.Part`
    * ``compiled_content`` -- The compiled HTML generated from the ReST ``content``
    * ``content`` -- The ReST content for the :class:`~wte.models.Part`
    * ``order`` -- The ordering position of this :class:`~wte.models.Part`
    * ``parent_id`` -- The unique database identifier of the parent :class:`~wte.models.Part`
    * ``parent`` -- The parent :class:`~wte.models.Part`
    * ``progress`` -- The :class:`~wte.models.UserPartProgress` linked to this :class:`~wte.models.Part`
    * ``status`` -- The :class:`~wte.models.Part`'s availability status
    * ``tasks`` -- List of :class:`~wte.models.TimedTask` that are attached to this
      :class:`~wte.models.Part`
    * ``templates`` -- List of :class:`~wte.models.Asset` that act as template files
    * ``title`` -- The title displayed for this :class:`~wte.models.Part`
    * ``type`` -- Whether the :class:`~wte.models.Part` is a module, tutorial, page,
      exercise, or task.
    * ``users`` -- The :class:`~wte.models.User` that are linked to this :class:`~wte.models.Part`
    """
    __tablename__ = u'parts'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey(u'parts.id', name=u'parts_parent_id_fk'))
    order = Column(Integer)
    title = Column(Unicode(255))
    status = Column(Unicode(255))
    type = Column(Unicode(255))
    content = Column(UnicodeText)
    compiled_content = Column(UnicodeText)

    children = relationship(u'Part',
                            backref=backref(u'parent', remote_side=[id]),
                            cascade=u'all,delete',
                            order_by=u'Part.order')
    templates = relationship(u'Asset',
                             secondary=u'parts_assets',
                             secondaryjoin=u"and_(Asset.id==parts_assets.c.asset_id, Asset.type=='template')",
                             order_by=u'Asset.order',
                             viewonly=True)
    assets = relationship(u'Asset',
                          secondary=u'parts_assets',
                          secondaryjoin=u"and_(Asset.id==parts_assets.c.asset_id, Asset.type=='asset')",
                          order_by=u'Asset.order',
                          viewonly=True)
    all_assets = relationship(u'Asset',
                              cascade=u'all',
                              secondary=u'parts_assets',
                              backref=u'parts')
    users = relationship(u'UserPartRole',
                         cascade=u'all')
    progress = relationship(u'UserPartProgress',
                            cascade=u'all',
                            primaryjoin=u'Part.id==UserPartProgress.part_id')
    tasks = relationship(u'TimedTask',
                         cascade=u'all')

    def root(self):
        u"""Gets the root :class:`~wte.models.Part` for the current :class:`~wte.models.Part`.
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
        ``action``. Supports the following action: view.

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
        if action == u'view':
            root = self.root()
            if user.has_permission('admin.modules.view'):
                return True
            elif root.has_role(['owner', 'tutor'], user):
                return True
            elif root.has_role('student', user):
                if self.status in [u'available', u'archived']:
                    return True
            elif self.type == u'module' and self.status == u'available':
                return True
        elif action == u'edit':
            if user.has_permission('admin.modules.edit'):
                return True
            elif self.has_role(u'owner', user):
                return True
            elif self.parent:
                return self.parent.allow(action, user)
        elif action == u'delete':
            if user.has_permission('admin.modules.delete'):
                return True
            elif self.has_role(u'owner', user):
                return True
            elif self.parent:
                return self.parent.allow(action, user)
        elif action == u'users':
            if self.type == u'module':
                if self.has_role('owner', user):
                    return True
                else:
                    return False
            elif self.parent:
                self.parent.allow(action, user)
        return False

    def has_role(self, role, user):
        u"""Checks if the given ``user`` has the given ``role`` for this :class:`~wte.models.Part`.
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

Index('parts_parent_id_ix', Part.parent_id)


class UserPartProgress(Base):
    u"""The :class:`~wte.models.UserPartProgress` represents the progress a
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

    __tablename__ = u'user_part_progress'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, name=u'user_part_progress_user_id_fk'))
    part_id = Column(Integer, ForeignKey(Part.id, name=u'user_part_progress_part_id_fk'))
    current_id = Column(Integer, ForeignKey(Part.id, name=u'user_part_progress_current_id_fk'))

    user = relationship(u'User')
    part = relationship(u'Part', foreign_keys=[part_id])
    current = relationship(u'Part', foreign_keys=[current_id])
    files = relationship(u'Asset',
                         cascade="all",
                         secondary=u'progress_assets',
                         order_by=u'Asset.order')

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
    u"""The class:`~wte.models.Asset` represents any kind of file data. What role the
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

    __tablename__ = u'assets'

    id = Column(Integer, primary_key=True)
    type = Column(Unicode(255))
    filename = Column(Unicode(255))
    mimetype = Column(Unicode(255))
    order = Column(Integer)
    data = Column(LargeBinary)

Index(u'assets_filename_ix', Asset.filename)
Index(u'assets_type_ix', Asset.type)


parts_assets = Table('parts_assets', Base.metadata,
                     Column('part_id',
                            ForeignKey('parts.id',
                                       name='parts_assets_part_id_fk'),
                            primary_key=True),
                     Column('asset_id',
                            ForeignKey('assets.id',
                                       name='parts_assets_asset_id_fk'),
                            primary_key=True))
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.Part` and
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
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.Part` and
:class:`~wte.models.Asset`.
"""


class TimedTask(Base):
    u"""The class:`~wte.models.TimedTask` represents a task that is to be run at a specific
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
