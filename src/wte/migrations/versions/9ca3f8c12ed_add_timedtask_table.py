"""
####################################################
Add the table for the :class:`~wte.models.TimedTask`
####################################################

Revision ID: 9ca3f8c12ed
Revises:
Create Date: 2015-04-19 17:23:25.260970

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9ca3f8c12ed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('timed_tasks',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('part_id', sa.Integer, sa.ForeignKey('parts.id',
                                                                   name='timed_tasks_part_id_fk')),
                    sa.Column('name', sa.Unicode(255)),
                    sa.Column('title', sa.Unicode(255)),
                    sa.Column('timestamp', sa.DateTime, index=True),
                    sa.Column('_options', sa.UnicodeText),
                    sa.Column('status', sa.Unicode(255), index=True))
    op.create_index('ix_timed_tasks_timestamp_status', 'timed_tasks',
                    ['timestamp', 'status'])


def downgrade():
    op.drop_table('timed_tasks')
