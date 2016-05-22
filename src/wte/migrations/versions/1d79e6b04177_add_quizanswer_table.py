"""
####################
Add QuizAnswer table
####################

Add the "quiz_answers" table that backs the :class:`~wte.models.QuizAnswer` model.

Revision ID: 1d79e6b04177
Revises: 58f6e5c75e86
Create Date: 2016-05-21 17:40:50.898042

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1d79e6b04177'
down_revision = '58f6e5c75e86'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('quiz_answers',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('part_id', sa.Integer, sa.ForeignKey('parts.id',
                                                                   name='quiz_answers_part_id_fk')),
                    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id',
                                                                   name='quiz_answers_user_id_fk')),
                    sa.Column('quiz', sa.Unicode(255)),
                    sa.Column('question', sa.Unicode(255)),
                    sa.Column('initial_answer', sa.Unicode(255)),
                    sa.Column('initial_correct', sa.Boolean),
                    sa.Column('final_answer', sa.Unicode(255)),
                    sa.Column('final_correct', sa.Boolean),
                    sa.Column('attempts', sa.Integer))
    op.create_index('quiz_answers_full_ix', 'quiz_answers',
                    ['part_id', 'user_id', 'quiz', 'question'])


def downgrade():
    op.drop_table('quiz_answers')
