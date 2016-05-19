"""
######################
Add "admin" permission
######################

Add an "admin" :class:`~wte.models.Permission` and link it to the "User Admin"
and "Content Admin" :class:`~wte.models.PermissionGroup`. Also rename the
"User Admin" and "Content Admin" to "User Administration" and "Content
Administration" respectively.

Revision ID: 4b401085b9e3
Revises: 9ca3f8c12ed
Create Date: 2015-05-17 14:53:55.468524

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4b401085b9e3'
down_revision = '9ca3f8c12ed'
branch_labels = None
depends_on = None

metadata = sa.MetaData()

p = sa.Table('permissions', metadata,
             sa.Column('id', sa.Integer, primary_key=True),
             sa.Column('name', sa.Unicode(255), unique=True),
             sa.Column('title', sa.Unicode(255)))
pg = sa.Table('permission_groups', metadata,
              sa.Column('id', sa.Integer, primary_key=True),
              sa.Column('title', sa.Unicode(255)))
pg_p = sa.Table('permission_groups_permissions', metadata,
                sa.Column('permission_group_id', sa.Integer, primary_key=True),
                sa.Column('permission_id', sa.Integer, primary_key=True))


def upgrade():
    bind = op.get_bind()
    metadata.bind = bind
    aa_pk = bind.execute(p.insert().values(name='admin', title='Administration Access')).inserted_primary_key[0]
    user_admin_group = bind.execute(pg.select().where(pg.c.title == 'User Admin')).first()
    bind.execute(pg_p.insert().values(permission_group_id=user_admin_group.id, permission_id=aa_pk))
    content_admin_group = bind.execute(pg.select().where(pg.c.title == 'Content Admin')).first()
    bind.execute(pg_p.insert().values(permission_group_id=content_admin_group.id, permission_id=aa_pk))
    bind.execute(pg.update().values(title='User Administration').where(pg.c.id == user_admin_group.id))
    bind.execute(pg.update().values(title='Content Administration').where(pg.c.id == content_admin_group.id))


def downgrade():
    bind = op.get_bind()
    metadata.bind = bind
    admin_permission = bind.execute(p.select().where(p.c.name == 'admin')).first()
    user_admin_group = bind.execute(pg.select().where(pg.c.title == 'User Administration')).first()
    content_admin_group = bind.execute(pg.select().where(pg.c.title == 'Content Administration')).first()
    bind.execute(pg_p.delete().where(sa.and_(pg_p.c.permission_group_id == user_admin_group.id,
                                             pg_p.c.permission_id == admin_permission.id)))
    bind.execute(pg_p.delete().where(sa.and_(pg_p.c.permission_group_id == content_admin_group.id,
                                             pg_p.c.permission_id == admin_permission.id)))
    bind.execute(p.delete().where(p.c.name == 'admin'))
    bind.execute(pg.update().values(title='User Admin').where(pg.c.id == user_admin_group.id))
    bind.execute(pg.update().values(title='Content Admin').where(pg.c.id == content_admin_group.id))
