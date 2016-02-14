(function($) {
    /**
     * The dropdownMenu jQuery plugin provides a drop-down GUI menu.
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var component = $(this);
                var menu = component.children('ul');
                var button = component.children('a');
                component.data('wte-menu', menu);
                component.data('wte-menu-button', button);
                menu.css('width', menu.outerWidth() + 'px').css('position', 'absolute');
                menu.hide();
                button.on('click', function(ev) {
                    ev.preventDefault(true);
                    component.dropdownMenu('show');
                });
            });
        },
        show : function() {
            return this.each(function() {
                var component = $(this);
                var menu = component.data('wte-menu');
                component.css('z-index', '100');
                if (component.data('wte-menu-position') == 'right') {
                    menu.show().position({
                        my : 'right top',
                        at : 'right bottom',
                        of : component.data('wte-menu-button')
                    });
                } else {
                    menu.show().position({
                        my : 'left top',
                        at : 'left bottom',
                        of : component.data('wte-menu-button')
                    });
                }
                setTimeout(function() {
                    $(document).on('click.wte-menu', function(ev) {
                        component.dropdownMenu('hide');
                    });
                }, 100);
            });
        },
        hide : function() {
            return this.each(function() {
                var component = $(this);
                var menu = component.data('wte-menu');
                component.css('z-index', '');
                menu.hide();
                $(document).off('click.wte-menu');
            });
        }
    };

    $.fn.dropdownMenu = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.dropdownMenu');
        }
    };
}(jQuery));

/**
 * Generates a new CodeMirror instance for the given textarea.
 * 
 * @param textarea A jQuery object with a single textarea.
 * @returns The new CodeMirror instance
 */
function codemirror_for_textarea(textarea) {
    var options = {
            mode: textarea.data('wte-mimetype'),
            lineNumbers: true,
            indentUnit: 4,
    };
    var override_options = textarea.data('wte-cm-options');
    if(override_options) {
        options = $.extend(options, override_options);
    }
    var cm = CodeMirror.fromTextArea(textarea[0], options);
    cm.setOption("extraKeys", {
        'Tab': function(cm) {
            if(cm.somethingSelected()) {
                cm.indentSelection("add");
                return;
            } else {
                cm.execCommand("insertSoftTab");
            }
        },
        'Shift-Tab': function(cm) {
            cm.indentSelection("subtract");
        }
    });
    return cm;
}

(function($) {
    /**
     * The tabbedEditor jQuery plugin provides the tabbed editor functionality.
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var component = $(this);
                component.data('wte-options', options);
                component.find('textarea').each(function() {
                    var textarea = $(this);
                    var tab = component.find('#' + textarea.parent().attr('id') + '-tab');
                    var cm = codemirror_for_textarea(textarea);
                    cm.on('change', function(cm, changes) {
                        clearTimeout(textarea.data('wte-timeout'));
                        tab.removeClass('saved');
                        tab.removeClass('saving');
                        tab.addClass('modified');
                        textarea.data('wte-timeout', setTimeout(function() {
                            component.tabbedEditor('save', tab, textarea);
                            }, 10000));
                    });
                    textarea.data('wte-cm', cm);
                });
                component.find('.tabs a.save').on('click', function(event) {
                	event.preventDefault();
                	var link = $(this);
                	var tab = link.parents('dd');
                	var tab_id = tab.attr('id');
                	tab_id = tab_id.substring(0, tab_id.length - 4);
                	var textarea = component.find('#' + tab_id + ' > textarea');
                	component.tabbedEditor('save', tab, textarea);
                });
                component.find('.tabs').on('toggled', function(event, tab) {
                	var tab_id = tab.children('a').attr('href').substr(1);
                    $('#' + tab_id).children('textarea').data('wte-cm').refresh();
                });
                options.viewer.on('load', function() {
                    options.viewer.contents().scrollTop(component.data('wte-viewer-scroll-top'));
                    component.tabbedEditor('save_scroll');
                });
            });
        },
        save : function(tab, textarea) {
            return this.each(function() {
                var component = $(this);
                clearTimeout(textarea.data('wte-timeout'));
                tab.removeClass('saved');
                tab.addClass('saving');
                tab.removeClass('modified');
                url = component.data('wte-options').save_url;
                url = url.replace('FID', textarea.data('wte-fileid'));
                clearTimeout(component.data('wte-viewer-scroll-timeout'));
                $.ajax(url, {
                    type : 'POST',
                    data : {
                        'content' : textarea.data('wte-cm').getValue()
                    },
                    dataType : 'json'
                }).complete(function() {
                    var iframe = component.data('wte-options').viewer;
                    iframe.attr('src', iframe.attr('src'));
                    tab.addClass('saved');
                    textarea.data('wte-timeout', setTimeout(function() {
                        tab.removeClass('saved');
                    }, 3000));
                }).always(function() {
                    tab.removeClass('saving');
                });
            });
        },
        save_scroll : function() {
            return this.each(function() {
                var component = $(this);
                component.data('wte-viewer-scroll-top', component.data('wte-options').viewer.contents().scrollTop());
                component.data('wte-viewer-scroll-timeout', setTimeout(function() {
                    component.tabbedEditor('save_scroll');
                }, 100));
            });
        }
    };

    $.fn.tabbedEditor = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.dropdownMenu');
        }
    };
}(jQuery));

(function($) {
    /**
     * The postLink jQuery plugin provides automatic submission of a standard
     * link via a POST request. If a data-wte-confirm attribute is present on
     * the link, then the user has to confirm the action. The data-wte-confirm
     * attribute should look like this:
     * 
     * {"title": "Title string", "msg": "Main message string", "cancel":
     * {"label": "Cancel button label string", "class": "CSS classes"}, "ok":
     * {"label": "Ok button label string", "class": "CSS classes"}}
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var component = $(this);
                component.on('click', function(ev) {
                    ev.preventDefault();
                    var confirm = component.data('wte-confirm');
                    if (confirm) {
                        var html = '<div class="reveal-modal" data-reveal="">'
                                + '<h2>' + (confirm.title || 'Please confirm')
                                + '</h2>' + '<p>' + confirm.msg + '</p>'
                                + '<div class="text-right">';
                        if (confirm.cancel) {
                            html = html + '<a href="#" class="button cancel '
                                    + (confirm.cancel.class_ || '') + '">'
                                    + (confirm.cancel.label || 'Cancel')
                                    + '</a>&nbsp;';
                        }
                        if (confirm.ok) {
                            html = html + '<a href="#" class="button ok '
                                    + (confirm.ok.class_ || '') + '">'
                                    + (confirm.ok.label || 'Ok') + '</a>';
                        }
                        html = html + '</div>' + '</div>';
                        var dlg = $(html);
                        $('body').append(dlg);
                        dlg.find('a.cancel').on('click', function(ev) {
                            ev.preventDefault();
                            dlg.foundation().foundation('reveal', 'close');
                        });
                        dlg.find('a.ok').on('click', function(ev) {
                            ev.preventDefault();
                            var frm = $('<form action="'
                                    + component.attr('href')
                                    + '" method="post"></form>');
                            $('body').append(frm);
                            frm.submit();
                        });
                        dlg.foundation().foundation('reveal', 'open');
                        $(document).on('closed.fndtn.reveal', '[data-reveal]', function() {
                            dlg.remove();
                        });
                    } else {
                        var frm = $('<form action="' + component.attr('href')
                                + '" method="post"></form>');
                        $('body').append(frm);
                        frm.submit();
                    }
                });
            });
        }
    };

    $.fn.postLink = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.postLink');
        }
    };
}(jQuery));

(function($) {
    /**
     * The fancyFlash jQuery plugin provides a more fancy display of the flash messages.
     */
    var methods = {
        init : function(options) {
            return this.each(function() {
                var component = $(this);
                setTimeout(function() {
                    component.find('.column, .columns').addClass('minimise');
                }, 5000);
            });
        }
    };

    $.fn.fancyFlash = function(method) {
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || !method) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Method ' + method + ' does not exist on jQuery.fancyFlash');
        }
    };
}(jQuery));

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
                    form.attr('action', form.attr('action').replace('pid', select.val()));
                    form.submit();
                });
                if(options && options.scrolling) {
                    var progress = component.data('progress');
                    progress.diff = progress.max - progress.min;
                    var height = 0;
                    if(options.scrolling[0] == window) {
                    	$('body').children().each(function() {
                    		if($(this).is(':visible')) {
                        		console.log($(this));
                        		console.log($(this).outerHeight(true));
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
                    	component.find('.meter').css('width', perc + '%');
                    });
                	var perc = Math.min(progress.min + (progress.diff / height * options.scrolling.scrollTop()),
                			progress.max);
                	component.find('.meter').css('width', perc + '%');
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
