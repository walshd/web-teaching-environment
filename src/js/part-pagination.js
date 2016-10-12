(function($) {
    /**
     * The partPagination jQuery plugin handles the pagination between Parts. It also
     * handles the updating the progress bar based on the scrolling progress in the
     * container specified via the "scrolling" option.
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var component = $(this);
                var form = component.find('form');
                form.find('select').on('change', function() {
                    var select = $(this);
                    form.attr('action', form.attr('action').replace('PID', select.val()));
                    form.submit();
                });
                if(options && options.scrolling) {
                    var progress = component.data('progress');
                    progress.diff = progress.max - progress.min;
                    var height = 0;
                    if(options.scrolling[0] == window) {
                        $('body').children().each(function() {
                            if($(this).is(':visible')) {
                            height = height + $(this).outerHeight(true);
                            }
                        });
                    } else {
                        options.scrolling.children().each(function() {
                            height = height + $(this).outerHeight(true);
                        });
                    }
                    height = height - options.scrolling.innerHeight();
                    options.scrolling.on('scroll', function() {
                        var perc = Math.min(progress.min + (progress.diff / height * options.scrolling.scrollTop()),
                                progress.max);
                        component.find('.progress-meter').css('width', perc + '%');
                        component.find('.progress').attr('aria-valuenow', perc);
                    });
                    var perc = Math.min(progress.min + (progress.diff / height * options.scrolling.scrollTop()),
                            progress.max);
                    component.find('.progress-meter').css('width', perc + '%');
                    component.find('.progress').attr('aria-valuenow', perc);
                }
            });
        }
    };

    $.fn.partPagination = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.partPagination');
        }
    };
}(jQuery));
