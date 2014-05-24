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
import random
import hashlib

from sqlalchemy import (Column, Index, ForeignKey, Integer, Unicode,
                        UnicodeText, Table)
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.event import listens_for
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship,
                            reconstructor)
from zope.sqlalchemy import ZopeTransactionExtension

from wte.text_formatter import compile_rst

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

DB_VERSION = u''
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
                result = dbsession.query('version_num').from_statement('SELECT version_num FROM alembic_version').first()
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
    modules = relationship('UserModuleRole', backref=u'user', cascade=u'all,delete')
    
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
        self.salt = u''.join(unichr(random.randint(0, 127)) for _ in range(32))
        if password:
            self.new_password(password)
        else:
            self.password = u''
        self.login_limit = 0
        self.preferences_ = {}
    
    @reconstructor
    def init(self):
        self.preferences_ = {}
        
    def new_password(self, password):
        """Sets the given ``password`` as the :class:`~wte.models.User`'s new
        password. Will also generate a new :data:`~wte.models.User.salt`.
        
        :param password: The new cleartext password
        :type password: `unicode`
        """
        self.salt = u''.join(unichr(random.randint(0, 127)) for _ in range(32))
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
        direct_perm = dbsession.query(Permission.name).join(User, Permission.users).filter(User.id==self.id)
        group_perm = dbsession.query(Permission.name).join(PermissionGroup, Permission.permission_groups).join(User, PermissionGroup.users).filter(User.id==self.id)
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
            return True # TODO: Add support for showing / hiding profile
        elif action == 'edit':
            return user.has_permission('admin.users.edit')
        elif action == 'delete':
            return user.has_permission('admin.users.delete')
        return False

Index('users_email_ix', User.email)
    
users_permissions = Table('users_permissions', Base.metadata,
                          Column('user_id', ForeignKey('users.id', name='users_permissions_users_fk'), primary_key=True),
                          Column('permission_id', ForeignKey('permissions.id', name='users_permissions_permissions_fk'), primary_key=True))
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
                           Column('permission_group_id', ForeignKey(PermissionGroup.id, name='permission_groups_permissions_groups_fk'), primary_key=True),
                           Column('permission_id', ForeignKey(Permission.id, 'permission_groups_permissions_permissions_fk'), primary_key=True))
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.PermissionGroup` and
:class:`~wte.models.Permission`.
"""

users_groups = Table('users_permission_groups', Base.metadata,
                     Column('user_id', ForeignKey(User.id, name='users_permission_groups_users_fk'), primary_key=True),
                     Column('permission_group_id', ForeignKey(PermissionGroup.id, name='users_permission_groups_groups_fk'), primary_key=True))
u""":class:`sqlalchemy.Table` to link :class:`~wte.models.User` and
:class:`~wte.models.PermissionGroup`.
"""

class UserModuleRole(Base):
    
    __tablename__ = u'users_modules'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id, name=u'users_modules_user_id_fk'))
    module_id = Column(Integer, ForeignKey('modules.id', name=u'users_modules_module_id_fk'))
    role = Column(Unicode(255))
    
class Module(Base):
    u"""The :class:`~wte.models.Module` class represents a teaching module that
    contains one or more :class:`~wte.models.Part`.
    
    Instances of :class:`~wte.models.Module` have the following attributes:
    
    * ``id`` -- The unique database identifier
    * ``owner_id`` -- The unique database identifier of the
      :class:`~wte.models.User` who created this :class:`~wte.models.Module`
    * ``owner`` -- The :class:`~wte.models.User` who created this
      :class:`~wte.models.Module`
    * ``status`` -- The status determines the access level
    * ``title`` -- The title displayed for this :class:`~wte.models.Module`
    * ``tutorials`` -- List of :class:`~wte.models.Part` contained in this
      :class:`~wte.models.Module`
    """
    __tablename__ = u'modules'
    
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(255))
    status = Column(Unicode(255))
    
    users = relationship(u'UserModuleRole', backref=u'module', cascade=u'all,delete')
    parts = relationship(u'Part', backref=u'module', cascade=u'all,delete', order_by=u'Part.order')
    
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
        for user_asc in self.users:
            if user_asc.user == user:
                if action == u'view':
                    return True
                elif action == u'edit' and user_asc.role == u'owner':
                    return True
                elif action == u'delete' and user_asc.role == u'owner':
                    return True
        return False

class Part(Base):
    u"""The :class:`~wte.models.Part` class represents either a tutorial or
    exercise. If a tutorial, then it consists of one or more
    :class:`~wte.models.Page`.
    
    Instances of :class:`~wte.models.Part` have the following attributes:
    
    * ``id`` -- The unique database identifier
    * ``module_id`` -- The unique identifier of the :class:`~wte.models.Module`
      that contains this :class:`~wte.models.Part`
    * ``module`` -- The :class:`~wte.models.Module` that contains this
      :class:`~wte.models.Part`
    * ``order`` -- The ordering position of this :class:`~wte.models.Part`
    * ``pages`` -- List of :class:`~wte.models.Page` contained in this
      :class:`~wte.models.Part`
    * ``status`` -- The :class:`~wte.models.Part`'s availability status
    * ``title`` -- The title displayed for this :class:`~wte.models.Part`
    * ``type`` -- Whether the :class:`~wte.models.Part` is a tutorial or
      exercise.
    """
    __tablename__ = u'parts'
    
    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey(u'modules.id', name=u'sessions_module_id_fk'))
    order = Column(Integer)
    title = Column(Unicode(255))
    status = Column(Unicode(255))
    type = Column(Unicode(255))
    
    pages = relationship(u'Page', backref=u'part', cascade=u'all,delete', order_by='Page.order')

Index('parts_module_id_ix', Part.module_id)

class Page(Base):
    u"""The :class:`~wte.models.Page` class represents a single page in a
    :class:`~wte.models.Part`.
    
    Instances of :class:`~wte.models.Page` have the following attributes:
    
    * ``id`` -- The unique database identifier
    * ``compiled_content`` -- The compiled HTML content to display
    * ``content`` -- The raw ReST text content of this
      :class:`~wte.models.Page`
    * ``order`` -- The ordering position of this :class:`~wte.models.Part`
    * ``title`` -- The title displayed for this :class:`~wte.models.Part`
    * ``tutorial_id`` -- The unique database identifier of the 
      :class:`~wte.models.Part` that contains this
      :class:`~wte.models.Page`
    * ``tutorial`` -- The :class:`~wte.models.Part` that contains this
      :class:`~wte.models.Page`
    """
    __tablename__ = u'pages'
    
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey(u'parts.id', name=u'pages_part_id_fk'))
    order = Column(Integer)
    title = Column(Unicode(255))
    content = Column(UnicodeText)
    compiled_content = Column(UnicodeText)

Index('pages_part_id_ix', Page.part_id)

@listens_for(Page.content, 'set')
def compile_page_content(target, value, old_value, initiator):
    u"""SQLAlchemy event listener that automatically compiles the ReST content
    of a :class:`~wte.models.Page` to HTML when it is set / updated."""
    target.compiled_content = compile_rst(value)
