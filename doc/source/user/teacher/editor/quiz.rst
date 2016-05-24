In-Tutorial Quizes
------------------

The Web Teaching Environment lets you create small quizzes as part of the main content
of a module, tutorial, or page. The quiz system currently allows single or multiple
choice questions with one or more correct answers per question.

To create a new Quiz use the following ReST:

.. sourcecode:: rest

  .. quiz:: quiz-identifier
     :title: This is the quiz's title

The ``quiz-identifier`` must consist only of letters and numbers. The ``title`` can consist
of any content you wish to use.

To add questions to the quiz, include ``quiz-question`` entries in the ``quiz``:

.. sourcecode:: rest

  .. quiz:: quiz-identifier
     :title: This is the quiz's title
     
     .. quiz-question:: question-identifier-1
        :type: single-choice
        :question: Select one of these options
        
        [x] Answer 1
        Answer 2
        Answer 3
     
     .. quiz-question:: question-identifier-2
        :type: multi-choice
        :question: Select all options that are correct
        
        Answer 1
        [x] Answer 2
        [x] Answer 3
        Answer 4
 
 The ``question-identifier-1`` must consist only of letters and numbers. The ``question`` can
 consist of any content you wish to use. The ``type`` must be either "single-choice" for a
 single-choice question or "multi-choice" for a multi-choice question.
 
 Each line in the ``quiz-question`` is shown as one potential answer. Use "[x]" at the beginning
 of those answers that are correct. For single choice questions, you can only mark one question
 as correct. For multiple choice questions you can mark multiple answers as correct. The learner
 has to select all correct answers and none of the incorrect answers in order for the question
 to be judged to be correct overall. 
 