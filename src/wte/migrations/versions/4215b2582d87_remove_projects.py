"""
###################################
Remove Project Creation Permissions
###################################

Remove the 'project.create' :class:`~wte.models.Permission` and unlink it from
all :class:`~wte.models.PermissionGroup` and :class:`~wte.models.User`.

Revision ID: 4215b2582d87
Revises: 36a393fca848
Create Date: 2015-06-02 11:28:17.116785

"""

# revision identifiers, used by Alembic.
revision = '4215b2582d87'
down_revision = '36a393fca848'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

metadata = sa.MetaData()
p = sa.Table('permissions', metadata,
             sa.Column('id', sa.Integer, primary_key=True),
             sa.Column('name', sa.Unicode(255), unique=True),
             sa.Column('title', sa.Unicode(255)))
pg = sa.Table('permission_groups', metadata,
              sa.Column('id', sa.Integer, primary_key=True),
              sa.Column('title', sa.Unicode(255)))
p_u = sa.Table('users_permissions', metadata,
               sa.Column('user_id', sa.Integer, primary_key=True),
               sa.Column('permission_id', sa.Unicode(255)))
pg_p = sa.Table('permission_groups_permissions', metadata,
                sa.Column('permission_group_id', sa.Integer, primary_key=True),
                sa.Column('permission_id', sa.Integer, primary_key=True))


def upgrade():
    bind = op.get_bind()
    metadata.bind = bind
    pc_perm = bind.execute(p.select().where(p.c.name == 'projects.create')).first()
    bind.execute(p_u.delete().where(p_u.c.permission_id == pc_perm[0]))
    bind.execute(pg_p.delete().where(pg_p.c.permission_id == pc_perm[0]))
    bind.execute(p.delete().where(p.c.name == 'projects.create'))


def downgrade():
    bind = op.get_bind()
    metadata.bind = bind
    pc_pk = bind.execute(p.insert().values(name=u'projects.create',
                                           title=u'Create a new project')).inserted_primary_key[0]
    ca_g = bind.execute(pg.select().where(pg.c.title == 'Content Administration')).first()
    bind.execute(pg_p.insert().values(permission_group_id=ca_g[0], permission_id=pc_pk))
    s_g = bind.execute(pg.select().where(pg.c.title == 'Student')).first()
    bind.execute(pg_p.insert().values(permission_group_id=s_g[0], permission_id=pc_pk))
