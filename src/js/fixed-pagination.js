(function($) {
    /**
     * The fixedPagination jQuery plugin handles keeping a pagination at the
     * top of its parent when scrolling the parent
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var component = $(this);
                var top = component.position().top;
                var parent = component.parent();
                if(options && options.global) {
                    parent = $(window);
                    top = component.offset().top;
                }
                parent.on('scroll', function() {
                    var offset = Math.max(parent.scrollTop() - top, 0);
                    component.css('top', offset + 'px');
                });
                var offset = Math.max(parent.scrollTop() - top, 0);
                component.css('top', offset + 'px');
            });
        }
    };

    $.fn.fixedPagination = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.fixedPagination');
        }
    };
}(jQuery));
