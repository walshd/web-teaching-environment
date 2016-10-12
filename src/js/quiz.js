(function($) {
    /**
     * The quiz jQuery plugin handles the quiz validation.
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var form = $(this);
                // Handle the correctness checking
                form.on('submit', function(ev) {
                    ev.preventDefault();
                    var all_correct = true;
                    var all_wrong = true;
                    form.find('.question').each(function() {
                        var question = $(this);
                        var answers = question.data('answers');
                        var correct = true;
                        var answers_given = [];
                        question.find('input').each(function () {
                            var answer = $(this);
                            if(answer.is(':checked')) {
                                answers_given.push(answer.val());
                                if(answers.indexOf(answer.val()) < 0) {
                                    correct = false;
                                }
                            } else {
                                if(answers.indexOf(answer.val()) >= 0) {
                                    correct = false;
                                }
                            }
                        });
                        $.ajax(options.submit_url, {
                            data: {
                                quiz: form.data('quiz-id'),
                                question: question.data('question-id'),
                                answer: answers_given,
                                correct: correct,
                                csrf_token: options.csrf_token
                            },
                            type: 'post',
                            traditional: true
                         });
                        question.find('.title').find('.label').remove();
                        if(correct) {
                            question.find('.title').append('<span class="label correct"><span class="fi-check"> Correct</span></span>');
                            all_wrong = false;
                        } else {
                            question.find('.title').append('<span class="label incorrect"><span class="fi-x"> Incorrect</span></span>');
                            all_correct = false;
                        }
                    });
                    
                    form.children('.title').find('.label').remove();
                    if(all_correct) {
                        form.children('.title').append('<span class="label correct"><span class="fi-check"> You answered all questions correctly</span></span>')
                        form.find('.button').hide();
                    } else if(all_wrong) {
                        form.children('.title').append('<span class="label incorrect"><span class="fi-x"> Your answers are incorrect</span></span>')
                    } else {
                        form.children('.title').append('<span class="label partial"><span class="fi-check"> You answered some questions correctly</span></span>')
                    }
                });
                // Fetch whether the user has previously answered the questions and update the UI appropriately
                var all_correct = true;
                var all_wrong = true;
                form.find('.question').each(function() {
                    var question = $(this);
                    var promise = $.ajax(options.check_url, {
                        data: {
                            quiz: form.data('quiz-id'),
                            question: question.data('question-id'),
                            csrf_token: options.csrf_token
                        }
                    });
                    promise.then(function(data) {
                        if(data.status == 'correct') {
                            question.find('.title').append('<span class="label correct"><span class="fi-check"> Correct</span></span>');
                            all_wrong = false;
                        } else if(data.status == 'incorrect') {
                            question.find('.title').append('<span class="label incorrect"><span class="fi-x"> Incorrect</span></span>');
                            all_correct = false;
                        }
                        if(data.status && data.status != 'unanswered') {
                            form.children('.title').find('.label').remove();
                            if(all_correct === true) {
                                form.children('.title').append('<span class="label correct"><span class="fi-check"> You answered all questions correctly</span></span>')
                                form.find('.button').hide();
                            } else if(all_wrong === true) {
                                form.children('.title').append('<span class="label incorrect"><span class="fi-x"> Your answers are incorrect</span></span>')
                                form.find('.button').show();
                            } else if(all_correct === false && all_wrong === false){
                                form.children('.title').append('<span class="label partial"><span class="fi-check"> You answered some questions correctly</span></span>')
                                form.find('.button').show();
                            }
                        }
                        question.find('input').each(function() {
                            var answer = $(this);
                            if(data.answer && data.answer.indexOf(answer.val()) >= 0) {
                                answer.prop('checked', true);
                            } else {
                                answer.prop('checked', false);
                            }
                        });
                    });
                });
            })
        }
    };

    $.fn.quiz = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.quiz');
        }
    };
}(jQuery));
