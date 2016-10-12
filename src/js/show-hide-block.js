(function($) {
    /**
     * The showHideBlock jQuery plugin handles showing/hiding of the show-hide block elements.
     */
    var methods = {
        init: function(options) {
            return this.each(function() {
                var block = $(this);
                var menu = block.children('.menu');
                var content = menu.next();
                var show = menu.find('.show-block');
                var hide = menu.find('.hide-block');
                show.children('a').on('click', function(ev) {
                    ev.preventDefault();
                    show.hide();
                    hide.show();
                    content.slideDown();
                });
                hide.children('a').on('click', function(ev) {
                    ev.preventDefault();
                    hide.hide();
                    show.show();
                    content.slideUp();
                });
                if(block.data('show-hide-initial') == 'hidden') {
                    hide.hide();
                    content.hide();
                } else {
                    show.hide();
                }
            });
        }
    };

    $.fn.showHideBlock = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.showHideBlock');
        }
    };
}(jQuery));
