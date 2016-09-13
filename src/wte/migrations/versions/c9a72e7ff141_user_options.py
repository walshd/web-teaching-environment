"""
################
Add User options
################

Revision ID: c9a72e7ff141
Revises: 3ff51ab70eba
Create Date: 2016-08-14 16:19:41.435852
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c9a72e7ff141'
down_revision = '3ff51ab70eba'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('options', sa.UnicodeText))


def downgrade():
    op.drop_column('users', 'options')
