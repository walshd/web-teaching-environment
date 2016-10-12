(function($) {
    /**
     * The activityTimer jQuery plugin handles timing of the user's activity on a page.
     */
    var methods = {
        init: function(options) {
            return this.each(function() {
                var window = $(this);
                window.data('activity-timer-duration', 0);
                window.data('activity-timer-start', Date.now());
                window.on('mousemove', function() {
                    window.activityTimer('active');
                });
                window.on('keyup', function() {
                    window.activityTimer('active');
                });
                window.activityTimer('active');
                $(document).on('visibilitychange', function() {
                    if(document.visibilityState == 'visible') {
                        window.activityTimer('active');
                    } else {
                        window.activityTimer('inactive');
                    }
                });
            });
        },
        inactive: function() {
            return this.each(function() {
                var window = $(this);
                duration = Date.now() - window.data('activity-timer-start');
                window.data('activity-timer-duration', window.data('activity-timer-duration') + duration);
                window.data('activity-timer-start', undefined);
            });
        },
        active: function() {
            return this.each(function() {
                var window = $(this);
                clearTimeout(window.data('activity-timer'));
                window.data('activity-timer', setTimeout(function() {
                    window.activityTimer('inactive');
                }, 30000));
                if(window.data('activity-timer-start') === undefined) {
                    window.data('activity-timer-start', Date.now());
                }
            });
        },
        duration: function() {
            var window = this.first();
            duration = Date.now() - window.data('activity-timer-start');
            window.data('activity-timer-duration', window.data('activity-timer-duration') + duration);
            window.data('activity-timer-start', Date.now());
            return window.data('activity-timer-duration') + duration;
        },
        reset: function() {
            this.each(function() {
                var window = $(this);
                window.data('activity-timer-duration', 0);
                window.data('activity-timer-start', undefined);
                clearTimeout(window.data('activity-timer'));
            });
        }
    };

    $.fn.activityTimer = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.activityTimer');
        }
    };
}(jQuery));
