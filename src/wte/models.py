# -*- coding: utf-8 -*-

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

DB_VERSION = '6a2436d1eed'
"""The currently required database version."""

class DBUpgradeException(Exception):
    """The :class:`~pyquest.models.DBUpgradeException` is used to indicate that
    the database requires an upgrade before the Experiment Support System system
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
    by :data:`~pyquest.models.DB_VERSION`.
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
    """The :class:`~wte.models.User` represents all users in the WTE. Which
    functionality they can access is determined purely through the individual
    :class:`~wte.models.User`'s :class:`~wte.models.Permission`.
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
    
    def __init__(self, email, display_name, password=None):
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
        self.salt = u''.join(unichr(random.randint(0, 127)) for _ in range(32))
        self.password = unicode(hashlib.sha512('%s$$%s' % (self.salt, password)).hexdigest())
    
    def random_password(self):
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
        password = unicode(hashlib.sha512('%s$$%s' % (self.salt, password)).hexdigest())
        return password == self.password
    
    def has_permission(self, permission):
        dbsession = DBSession()
        direct_perm = dbsession.query(Permission.name).join(User, Permission.users).filter(User.id==self.id)
        group_perm = dbsession.query(Permission.name).join(PermissionGroup, Permission.groups).join(User, PermissionGroup.users).filter(User.id==self.id)
        return permission in map(lambda p: p[0], direct_perm.union(group_perm))
    
    def allow(self, action, user):
        if self.id == user.id:
            return True
        elif action == 'view':
            return True # TODO: Add support for showing / hiding profile
        elif action == 'edit':
            return user.has_permission('admin.users.edit')
        elif action == 'delete':
            return user.has_permission('admin.users.delete')
        return False
    
users_permissions = Table('users_permissions', Base.metadata,
                          Column('user_id', ForeignKey('users.id', name='users_permissions_users_fk'), primary_key=True),
                          Column('permission_id', ForeignKey('permissions.id', name='users_permissions_permissions_fk'), primary_key=True))

Index('users_email_ix', User.email)

class Permission(Base):
    
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(Unicode(255), unique=True)
    title = Column(Unicode(255))

Index('permissions_name_ix', Permission.name)

class PermissionGroup(Base):
    
    __tablename__ = 'permission_groups'
    
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(255))
    
    permissions = relationship('Permission', backref='groups', secondary='permission_groups_permissions')
    
groups_permissions = Table('permission_groups_permissions', Base.metadata,
                           Column('permission_group_id', ForeignKey(PermissionGroup.id, name='permission_groups_permissions_groups_fk'), primary_key=True),
                           Column('permission_id', ForeignKey(Permission.id, 'permission_groups_permissions_permissions_fk'), primary_key=True))

users_groups = Table('users_permission_groups', Base.metadata,
                     Column('user_id', ForeignKey(User.id, name='users_permission_groups_users_fk'), primary_key=True),
                     Column('permission_group_id', ForeignKey(PermissionGroup.id, name='users_permission_groups_groups_fk'), primary_key=True))

class Module(Base):
    
    __tablename__ = u'modules'
    
    id = Column(Integer, primary_key=True)
    title = Column(Unicode(255))
    
    tutorials = relationship(u'Tutorial', backref=u'module', order_by='Tutorial.order')

class Tutorial(Base):
    
    __tablename__ = u'tutorials'
    
    id = Column(Integer, primary_key=True)
    module_id = Column(Integer, ForeignKey(u'modules.id', name=u'sessions_module_id_fk'))
    order = Column(Integer)
    title = Column(Unicode(255))
    
    pages = relationship(u'Page', backref=u'tutorial', order_by='Page.order')
    
Index('sessions_modules_id_ix', Tutorial.module_id)

class Page(Base):
    
    __tablename__ = u'pages'
    
    id = Column(Integer, primary_key=True)
    tutorial_id = Column(Integer, ForeignKey(u'tutorials.id', name=u'pages_tutorial_id_fk'))
    order = Column(Integer)
    title = Column(Unicode(255))
    content = Column(UnicodeText)
    compiled_content = Column(UnicodeText)

Index('pages_tutorial_id_ix', Page.tutorial_id)

@listens_for(Page.content, 'set')
def compile_page_content(target, value, old_value, initiator):
    target.compiled_content = compile_rst(value)
