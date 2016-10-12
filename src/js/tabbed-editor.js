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
            $.error('Method ' + method + ' does not exist on jQuery.tabbedEditor');
        }
    };
}(jQuery));
