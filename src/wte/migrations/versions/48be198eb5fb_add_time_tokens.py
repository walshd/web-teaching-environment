"""
###############
Add Time Tokens
###############

Adds the :class:`~wte.models.TimeToken` table to the database.

Revision ID: 48be198eb5fb
Revises: 465d42577343
Create Date: 2016-05-16 15:47:01.559592

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '48be198eb5fb'
down_revision = '465d42577343'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('time_tokens',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id',
                                                                   name='time_tokens_user_id_fk')),
                    sa.Column('action', sa.Unicode(255)),
                    sa.Column('token', sa.Unicode(255)),
                    sa.Column('timeout', sa.DateTime()),
                    sa.Column('data', sa.UnicodeText()))
    op.create_index('time_tokens_full_ix', 'time_tokens',
                    ['action', 'token', 'timeout'])


def downgrade():
    op.drop_table('time_tokens')
