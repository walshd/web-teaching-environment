"""Change User validation process to have a status attribute, rather than guessing form the validation token

Revision ID: 58f6e5c75e86
Revises: 48be198eb5fb
Create Date: 2016-05-19 11:21:57.863003

"""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = '58f6e5c75e86'
down_revision = '48be198eb5fb'
branch_labels = None
depends_on = None

metadata = sa.MetaData()
users = sa.Table('users', metadata,
                 sa.Column('validation_token', sa.Unicode(255)),
                 sa.Column('status', sa.Unicode(255)))


def upgrade():
    bind = op.get_bind()
    metadata.bind = bind
    op.add_column('users', sa.Column('status', sa.Unicode(255)))
    bind.execute(users.update().values(status='active').where(users.c.validation_token == None))
    bind.execute(users.update().values(status='unconfirmed').where(users.c.validation_token != None))
    op.drop_column('users', 'validation_token')


def downgrade():
    bind = op.get_bind()
    metadata.bind = bind
    op.add_column('users', sa.Column('validation_token', sa.Unicode(255)))
    bind.execute(users.update().values(validation_token=uuid4().hex).where(users.c.status is 'unconfirmed'))
    op.drop_column('users', 'status')
