"""
##############################
Switch to Generic Module Parts
##############################

Add the "label" column to the :class:`~wte.models.Part` to enable
arbitrary classifiction of :class:`~wte.models.Part` for the user,
while simplifying the underlying :class:`~wte.models.Part` structure
to "Module" -> "Part" -> "Page".

Revision ID: 465d42577343
Revises: 510cc5b21636
Create Date: 2016-03-20 17:20:59.676226
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '465d42577343'
down_revision = '510cc5b21636'
branch_labels = None
depends_on = None

metadata = sa.MetaData()

parts = sa.Table('parts', metadata,
                 sa.Column('id', sa.Integer, primary_key=True),
                 sa.Column('type', sa.Unicode(255)),
                 sa.Column('display_mode', sa.Unicode(255)),
                 sa.Column('label', sa.Unicode(255)))


def upgrade():
    bind = op.get_bind()
    metadata.bind = bind
    op.add_column('parts', sa.Column('label', sa.Unicode(255), index=True))
    bind.execute(parts.update().values(label='exercise', type='part').where(parts.c.type == 'exercise'))
    bind.execute(parts.update().values(label='tutorial', type='part').where(parts.c.type == 'tutorial'))
    bind.execute(parts.update().values(type='page').where(parts.c.type == 'task'))
    bind.execute(parts.update().values(display_mode=None).where(parts.c.type == 'module'))
    bind.execute(parts.update().values(display_mode=None).where(parts.c.type == 'page'))


def downgrade():
    bind = op.get_bind()
    metadata.bind = bind
    bind.execute(parts.update().values(type='exercise').where(parts.c.label == 'exercise'))
    bind.execute(parts.update().values(type='tutorial').where(parts.c.label == 'tutorial'))
    bind.execute(parts.update().values(display_mode='default').where(parts.c.type == 'module'))
    bind.execute(parts.update().values(display_mode='inherit').where(parts.c.type == 'page'))
    op.drop_column('parts', 'label')
