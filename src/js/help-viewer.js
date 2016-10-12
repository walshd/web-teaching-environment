(function($) {
    /**
     * The helpViewer jQuery plugin handles the showing/hiding of
     * the help overlay.
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                $('#toggle-help').on('click', function(ev) {
                    ev.preventDefault();
                    $(document).helpViewer('toggle');
                });
                $('#help-viewer > a').on('click', function(ev) {
                    ev.preventDefault();
                    $(document).helpViewer('toggle');
                });
                $(window).on('keyup', function(ev) {
                    if(ev.keyCode == 27) {
                        $(document).helpViewer('toggle');
                    }
                });
                $(window).on('resize', function() {
                    $(document).helpViewer('resize');
                });
                $(window).on('scroll', function() {
                    if($(document).data('help-visible')) {
                        $(document).helpViewer('resize');
                    }
                });
            })
        },
        toggle: function() {
            $('#help-viewer').toggleClass('show');
            $(document).helpViewer('resize');
            $(document).data('help-visible', true);
        },
        resize: function() {
            $('#help-viewer').css('top', Math.max(10, 80 - $(window).scrollTop()) + 'px');
            $('#help-viewer').css('height', $(window).innerHeight() - $('#help-viewer').position().top - 10 + 'px');
        }
    };

    $.fn.helpViewer = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.helpViewer');
        }
    };
}(jQuery));
