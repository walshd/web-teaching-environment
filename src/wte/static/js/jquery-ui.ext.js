/**
 * Generates a new CodeMirror instance for the given textarea.
 * 
 * @param textarea A jQuery object with a single textarea.
 * @returns The new CodeMirror instance
 */
function codemirror_for_textarea(textarea) {
    var options = {
            mode: textarea.data('cm-mimetype'),
            lineNumbers: true,
            indentUnit: 4,
    };
    var override_options = textarea.data('cm-options');
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
                component.data('editor-options', options);
                component.find('textarea').each(function() {
                    var textarea = $(this);
                    var tab = component.find('#' + textarea.parents('.tabs-panel').attr('id') + '-tab');
                    var cm = codemirror_for_textarea(textarea);
                    cm.on('change', function(cm, changes) {
                        clearTimeout(textarea.data('editor-timeout'));
                        tab.removeClass('saved');
                        tab.removeClass('saving');
                        tab.addClass('modified');
                        textarea.data('editor-timeout', setTimeout(function() {
                            component.tabbedEditor('save', tab, textarea);
                        }, options.save_timeout || 10000));
                    });
                    textarea.data('editor-cm', cm);
                });
                component.find('.tabs-panel a.save').on('click', function(event) {
                	event.preventDefault();
                	var link = $(this);
                	var tab_id = link.parents('.tabs-panel').attr('id');
                        var tab = component.find('#' + tab_id + '-tab');
                	var textarea = component.find('#' + tab_id + ' .editor-wrapper > textarea');
                	component.tabbedEditor('save', tab, textarea);
                });
                component.find('.tabs').on('change.zf.tabs', function(event, tab) {
                    var link = tab.children('a')
                    var tab_id = link.attr('href');
                    $(tab_id).find('.editor-wrapper > textarea').data('editor-cm').refresh();
                    if(link.data('tab-filename')) {
                        var url = component.data('editor-options').viewer_url;
                        url = url.replace('FILENAME', link.data('tab-filename'));
                        var iframe = component.data('editor-options').viewer;
                        iframe.attr('src', url);
                    }
                });
                options.viewer.on('load', function() {
                    options.viewer.contents().scrollTop(component.data('editor-viewer-scroll-top'));
                    component.tabbedEditor('save_scroll');
                });
                component.on('keydown', function(ev) {
                    if(ev.key && ev.key.toLowerCase() == 's' && ev.ctrlKey) {
                        ev.preventDefault();
                        var tab = component.find('.tabs-title.is-active > a');
                        var textarea = component.find('.tabs-panel.is-active > .editor-wrapper > textarea');
                        component.tabbedEditor('save', tab, textarea);
                    }
                });
            });
        },
        save : function(tab, textarea) {
            return this.each(function() {
                var component = $(this);
                clearTimeout(textarea.data('editor-timeout'));
                textarea.parents('.tabs-panel').find('a.save span').removeClass('fi-save').addClass('fi-loop');
                tab.removeClass('saved');
                tab.addClass('saving');
                tab.removeClass('modified');
                url = component.data('editor-options').save_url;
                url = url.replace('FID', textarea.data('tab-fileid'));
                clearTimeout(component.data('editor-viewer-scroll-timeout'));
                $.ajax(url, {
                    type : 'POST',
                    data : {
                        'content' : textarea.data('editor-cm').getValue()
                    },
                    dataType : 'json'
                }).complete(function() {
                    var iframe = component.data('editor-options').viewer;
                    if(tab.data('tab-filename')) {
                        var url = component.data('editor-options').viewer_url;
                        url = url.replace('FILENAME', tab.data('tab-filename'));
                        iframe.attr('src', url);
                    } else {
                        iframe.attr('src', iframe.attr('src'));
                    }
                    tab.addClass('saved');
                    textarea.data('editor-timeout', setTimeout(function() {
                        tab.removeClass('saved');
                    }, 3000));
                }).always(function() {
                    textarea.parents('.tabs-panel').find('a.save span').removeClass('fi-loop').addClass('fi-save');
                    tab.removeClass('saving');
                });
            });
        },
        save_scroll : function() {
            return this.each(function() {
                var component = $(this);
                component.data('editor-viewer-scroll-top', component.data('editor-options').viewer.contents().scrollTop());
                component.data('editor-viewer-scroll-timeout', setTimeout(function() {
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
                        var html = '<div id="confirm-modal" class="reveal" data-reveal="">'
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
                        var reveal = new Foundation.Reveal(dlg);
                        dlg.find('a.cancel').on('click', function(ev) {
                            ev.preventDefault();
                            reveal.close();
                        });
                        dlg.find('a.ok').on('click', function(ev) {
                            ev.preventDefault();
                            var frm = $('<form action="'
                                    + component.attr('href')
                                    + '" method="post"></form>');
                            $('body').append(frm);
                            frm.submit();
                        });
                        $(document).on('closed.zf.reveal', function() {
                        	dlg.remove();
                        });
                        reveal.open();
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
            		$('#help-viewer').toggleClass('show');
            	});
            	$('#help-viewer > a').on('click', function(ev) {
            		ev.preventDefault();
            		$('#help-viewer').toggleClass('show');
            	});
            	$(window).on('keyup', function(ev) {
            		if(ev.keyCode == 27) {
                		$('#help-viewer').removeClass('show');
            		}
            	});
            	$(window).on('resize', function() {
            		$(document).helpViewer('resize');
            	});
            }).helpViewer('resize');
        },
        resize: function() {
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
