"""
#########################
Enable Part display modes
#########################

Add the "display_mode" column to the :class:`~wte.models.Part` to enable
different displays for the same type of :class:`~wte.models.Part`.

Revision ID: 36a393fca848
Revises: 4b401085b9e3
Create Date: 2015-06-01 14:27:42.790635

"""

# revision identifiers, used by Alembic.
revision = '36a393fca848'
down_revision = '4b401085b9e3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

metadata = sa.MetaData()
p = sa.Table('parts', metadata,
             sa.Column('id', sa.Integer, primary_key=True),
             sa.Column('type', sa.Unicode(255)),
             sa.Column('display_mode', sa.Unicode(255)))


def upgrade():
    bind = op.get_bind()
    metadata.bind = bind
    op.add_column('parts', sa.Column('display_mode', sa.Unicode(255)))
    bind.execute(p.update().values(display_mode='default'))
    bind.execute(p.update().values(display_mode='three_pane_html').where(p.c.type == 'tutorial'))
    bind.execute(p.update().values(display_mode='three_pane_html').where(p.c.type == 'exercise'))
    bind.execute(p.update().values(display_mode='three_pane_html').where(p.c.type == 'project'))
    bind.execute(p.update().values(display_mode='inherit').where(p.c.type == 'page'))
    bind.execute(p.update().values(display_mode='inherit').where(p.c.type == 'task'))


def downgrade():
    op.drop_column('parts', 'display_mode')
