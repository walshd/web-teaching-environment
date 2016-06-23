"""
###############################################
Add visited information to the UserPartProgress
###############################################

Add information for tracking the visited child :class:`~wte.models.Part`\ s to the
:class:`~wte.models.UserPartProgress`.

Revision ID: 3ff51ab70eba
Revises: 1d79e6b04177
Create Date: 2016-06-22 16:19:59.789303

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3ff51ab70eba'
down_revision = '1d79e6b04177'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_part_progress', sa.Column('visited', sa.UnicodeText()))


def downgrade():
    op.drop_column('user_part_progress', 'visited')
