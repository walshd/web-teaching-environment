"""
################
Add Asset E-Tags
################

Add the "etag" column to the :class:`~wte.models.Asset` to enable the use of
ETag and If-None-Match headers to reduce data traffic.

Revision ID: 10626db822ba
Revises: 4215b2582d87
Create Date: 2015-12-08 08:19:52.675176

"""

# revision identifiers, used by Alembic.
revision = '10626db822ba'
down_revision = '4215b2582d87'
branch_labels = None
depends_on = None

from alembic import op
import hashlib
import sqlalchemy as sa

metadata = sa.MetaData()
a = sa.Table('assets', metadata,
             sa.Column('id', sa.Integer, primary_key=True),
             sa.Column('data', sa.LargeBinary),
             sa.Column('etag', sa.Unicode(255)))


def upgrade():
    op.add_column('assets', sa.Column('etag', sa.Unicode(255)))
    bind = op.get_bind()
    metadata.bind = bind
    for asset in bind.execute(a.select()):
        if asset[1]:
            hash = hashlib.sha512(asset[1])
            bind.execute(a.update().values(etag=hash.hexdigest()).where(a.c.id == asset[0]))


def downgrade():
    op.drop_column('assets', 'etag')
