"""
###############
Add Quiz tables
###############

Add the "quiz" and "quiz_answers" table that back the :class:`~wte.models.Quiz` and
:class:`~wte.models.QuizAnswer` model.

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
    op.create_table('quizzes',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('part_id', sa.Integer, sa.ForeignKey('parts.id',
                                                                   name='quiz_answers_part_id_fk')),
                    sa.Column('name', sa.Unicode(255)))
    op.create_index('quizzes_full_ix', 'quizzes',
                    ['part_id', 'name'])
    op.create_table('quiz_answers',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id',
                                                                   name='quiz_answers_user_id_fk')),
                    sa.Column('quiz_id', sa.Integer, sa.ForeignKey('quizzes.id',
                                                                   name='quiz_answers_quiz_id_fk')),
                    sa.Column('question', sa.Unicode(255)),
                    sa.Column('initial_answer', sa.Unicode(255)),
                    sa.Column('initial_correct', sa.Boolean),
                    sa.Column('final_answer', sa.Unicode(255)),
                    sa.Column('final_correct', sa.Boolean),
                    sa.Column('attempts', sa.Integer))
    op.create_index('quiz_answers_full_ix', 'quiz_answers',
                    ['user_id', 'quiz_id', 'question'])


def downgrade():
    op.drop_table('quiz_answers')
    op.drop_table('quizzes')
