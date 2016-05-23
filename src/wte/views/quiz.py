# -*- coding: utf-8 -*-
"""
#####################################
:mod:`wte.views.quiz` -- Quiz Backend
#####################################

The :mod:`~wte.views.quiz` module provides the functionality for
storing answers to questions in the quiz functionality (see
:class:`~wte.text_formatter.docutils_ext.Quiz`.)

Routes are defined in :func:`~wte.views.quiz.init`.

.. moduleauthor:: Mark Hall <mark.hall@work.room3b.eu>
"""
import json
import transaction

from formencode import validators, Invalid, ForEach
from pyramid.view import view_config
from pywebtools.formencode import CSRFSchema, State
from pywebtools.pyramid.auth.views import current_user
from pywebtools.sqlalchemy import DBSession
from sqlalchemy import and_

from wte.decorators import (require_logged_in, require_method)
from wte.models import Quiz, QuizAnswer, Part


def init(config):
    """Adds the quiz-specific backend routes (route name, URL pattern
    handler):

    * ``quiz.set_answers`` -- ``/parts/{pid}/quiz/set_answers`` -- :func:`~wte.views.quiz.set_answers`
    * ``quiz.check_answers`` -- ``/parts/{pid}/quiz/check_answers`` -- :func:`~wte.views.quiz.check_answers`
    """
    config.add_route('quiz.set_answers', '/parts/{pid}/quiz/set_answers')
    config.add_route('quiz.check_answers', '/parts/{pid}/quiz/check_answers')


class SetAnswersSchema(CSRFSchema):
    """The :class:`~wte.views.quiz.SetAnswersSchema` validates requests to
    store a new answer for a :class:`~wte.text_formatter.docutils_ext.Quiz`.
    """

    quiz = validators.UnicodeString(not_empty=True)
    """The :class:`~wte.models.Quiz` name."""
    question = validators.UnicodeString(not_empty=True)
    """The :class:`~wte.models.Quiz` question."""
    answer = ForEach(validators.UnicodeString(if_empty='', if_missing=''))
    """The answer (can be given multiple times for multiple answers)."""
    correct = validators.StringBool(not_empty=True, if_missing=False, if_empty=False)
    """Whether the answer is correct or not."""


@view_config(route_name='quiz.set_answers', renderer='json')
@current_user()
@require_logged_in()
@require_method('POST')
def set_answers(request):
    """Handles the "/parts/{pid}/quiz/set_answers" URL and stores the answers to a
    :class:`~wte.text_formatter.docutils_ext.QuizQuestion`.

    If no previous :class:`~wte.models.QuizAnswer` exists, creates one and sets
    the initial answers / correctness to the data supplied. If one exists,
    then sets the final answer / correctness and updates the attempts count.
    """
    try:
        dbsession = DBSession()
        part = dbsession.query(Part).filter(Part.id == request.matchdict['pid']).first()
        if part and part.has_role('student', request.current_user):
            params = SetAnswersSchema().to_python(request.params,
                                                  State(request=request))
            with transaction.manager:
                quiz = dbsession.query(Quiz).filter(and_(Quiz.part_id == request.matchdict['pid'],
                                                         Quiz.name == params['quiz'])).first()
                if quiz is None:
                    quiz = Quiz(part_id = request.matchdict['pid'],
                                name = params['quiz'])
                    dbsession.add(quiz)
                answer = dbsession.query(QuizAnswer).filter(and_(QuizAnswer.user_id == request.current_user.id,
                                                                 QuizAnswer.quiz_id == quiz.id,
                                                                 QuizAnswer.question == params['question'])).first()
                if answer:
                    if not answer.initial_correct and not answer.final_correct:
                        answer.attempts = answer.attempts + 1
                        answer.final_answer = json.dumps(params['answer'])
                        answer.final_correct = params['correct']
                else:
                    dbsession.add(QuizAnswer(user_id=request.current_user.id,
                                             quiz=quiz,
                                             question=params['question'],
                                             initial_answer=json.dumps(params['answer']),
                                             initial_correct=params['correct'],
                                             final_answer=None,
                                             final_correct=None,
                                             attempts=1))
        return {}
    except Invalid as e:
        return {'errors': e.error_dict}


class CheckAnswerSchema(CSRFSchema):
    """The :class:`~wte.views.quiz.CheckAnswerSchema` checks whether the
    for the quiz and question there is an existing :class:`~wte.models.QuizAnswer`.
    """

    quiz = validators.UnicodeString(not_empty=True)
    """The name of the :class:`~wte.text_formatter.docutils_ext.Quiz` to check."""
    question = validators.UnicodeString(not_empty=True)
    """The name of the :class:`~wte.text_formatter.docutils_ext.QuizQuestion` to check."""


@view_config(route_name='quiz.check_answers', renderer='json')
@current_user()
@require_logged_in()
def check_answers(request):
    """Handles the "/parts/{pid}/quiz/check_answers" URL, checking whether a
    :class:`~wte.models.QuizAnswer` exists and if so, returning whether it was
    answered correctly and what the answer was.

    The response does not distinguish between initial or finally correct, but will return
    the last answer the user provided.
    """
    try:
        params = CheckAnswerSchema().to_python(request.params,
                                                State(request=request))
        dbsession = DBSession()
        quiz = dbsession.query(Quiz).filter(and_(Quiz.part_id == request.matchdict['pid'],
                                                 Quiz.name == params['quiz'])).first()
        if quiz:
            answer = dbsession.query(QuizAnswer).filter(and_(QuizAnswer.user_id == request.current_user.id,
                                                             QuizAnswer.quiz_id == quiz.id,
                                                             QuizAnswer.question == params['question'])).first()
            if answer:
                if answer.initial_correct:
                    return {'status': 'correct',
                            'answer': json.loads(answer.initial_answer)}
                elif answer.final_correct:
                    return {'status': 'correct',
                            'answer': json.loads(answer.final_answer)}
                elif answer.final_correct is None:
                    return {'status': 'incorrect',
                            'answer': json.loads(answer.initial_answer)}
                else:
                    return {'status': 'incorrect',
                            'answer': json.loads(answer.final_answer)}
        return {'status': 'unanswered'}
    except Invalid as e:
        return {'status': 'error',
                'errors': e.error_dict}
