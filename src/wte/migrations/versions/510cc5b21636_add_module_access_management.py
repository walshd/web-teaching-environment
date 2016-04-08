"""
#######################
Add Access Rights field
#######################

Add the "access_rights" column to the :class:`~wte.models.Part` to enable
nuanced access management for students taking a :class:`~wte.models.Part`.

Revision ID: 510cc5b21636
Revises: 10626db822ba
Create Date: 2015-12-26 16:05:16.548633

"""

# revision identifiers, used by Alembic.
revision = '510cc5b21636'
down_revision = '10626db822ba'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('parts', sa.Column('access_rights', sa.UnicodeText()))


def downgrade():
    op.drop_column('parts', 'access_rights')
