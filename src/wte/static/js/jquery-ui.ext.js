(function ($) {
	/**
	 * The dropdownMenu jQuery plugin provides a drop-down GUI menu.
	 */
	var methods = {
		init: function(options) {
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
		show: function() {
			return this.each(function() {
				var component = $(this);
				var menu = component.data('wte-menu');
				menu.show().position({
					my: 'left top',
					at: 'left bottom',
					of: component.data('wte-menu-button')
				});
				setTimeout(function() {
					$(document).on('click.wte-menu', function(ev) {
						component.dropdownMenu('hide');
					});
				}, 100);
			});
		},
		hide: function() {
			return this.each(function() {
				var component = $(this);
				var menu = component.data('wte-menu');
				menu.hide();
				$(document).off('click.wte-menu');
			});
		}
	};
		
	$.fn.dropdownMenu = function(method) {
	    if(methods[method]) {
	   		return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
	    } else if(typeof method === 'object' || !method) {
	   		return methods.init.apply(this, arguments);
	   	} else {
	   		$.error('Method ' +  method + ' does not exist on jQuery.dropdownMenu');
	   	}
	};
}(jQuery));

(function ($) {
	/**
	 * The tabbedEditor jQuery plugin provides the tabbed editor functionality.
	 */
	var methods = {
		init: function(options) {
			return this.each(function() {
				var component = $(this);
				component.data('wte-options', options);
				component.find('textarea').each(function() {
		            var textarea = $(this);
		            var tab = component.find('#' + textarea.parent().attr('id') + '-tab > a');
		            cm = CodeMirror.fromTextArea(this, {
		                mode: textarea.data('wte-mimetype')
		            });
		            cm.on('change', function(cm, changes) {
		                clearTimeout(textarea.data('wte-timeout'));
		                tab.css('color', '#aa0000');
		                textarea.data('wte-timeout', setTimeout(function() {component.tabbedEditor('save', tab, textarea);}, 1000));
		            });
		            textarea.data('wte-cm', cm);
				});
		        component.find('.tabs').on('toggled', function (event, tab) {
		            tab.children('textarea').data('wte-cm').refresh();
		        });
			});
		},
		save: function(tab, textarea) {
			return this.each(function() {
				var component = $(this);
				tab.find('img').show();
				url = component.data('wte-options').save_url;
		        url = url.replace('FID', textarea.data('wte-fileid'));
		        $.ajax(url, {
		            type: 'POST',
		            data: {'content': textarea.data('wte-cm').getValue()},
		            dataType: 'json'
		        }).complete(function() {
		            var iframe = component.data('wte-options').viewer;
		            iframe.attr('src', iframe.attr('src'));
					tab.css('color', '#0a0');
		            textarea.data('wte-timeout', setTimeout(function() {
						tab.css('color', '');
		            }, 3000));
		        }).always(function() {
					tab.find('img').hide();
		        });
			});
		}
	};
		
	$.fn.tabbedEditor = function(method) {
	    if(methods[method]) {
	   		return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
	    } else if(typeof method === 'object' || !method) {
	   		return methods.init.apply(this, arguments);
	   	} else {
	   		$.error('Method ' +  method + ' does not exist on jQuery.dropdownMenu');
	   	}
	};
}(jQuery));
