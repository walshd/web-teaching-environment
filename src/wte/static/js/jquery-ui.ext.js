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
				component.css('z-index', '100');
				if(component.data('wte-menu-position') == 'right') {
					menu.show().position({
						my: 'right top',
						at: 'right bottom',
						of: component.data('wte-menu-button')
					});
				} else {
					menu.show().position({
						my: 'left top',
						at: 'left bottom',
						of: component.data('wte-menu-button')
					});
				}
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
				component.css('z-index', '');
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

(function ($) {
	/**
	 * The postLink jQuery plugin provides automatic submission of a standard
	 * link via a POST request. If a data-wte-confirm attribute is present on the
	 * link, then the user has to confirm the action. The data-wte-confirm attribute
	 * should look like this:
	 * 
	 * {"title": "Title string", "msg": "Main message string",
	 *  "cancel": {"label": "Cancel button label string", "class": "CSS classes"},
	 *  "ok": {"label": "Ok button label string", "class": "CSS classes"}}
	 */
	var methods = {
		init: function(options) {
			return this.each(function() {
				var component = $(this);
				component.on('click', function(ev) {
					ev.preventDefault();
					var confirm = component.data('wte-confirm');
					if(confirm) {
						var html = '<div class="reveal-modal" data-reveal="">' +
							'<h2>' + (confirm.title || 'Please confirm') + '</h2>' +
							'<p>' + confirm.msg + '</p>' +
							'<div class="text-right">';
						if(confirm.cancel) {
							html = html + '<a href="#" class="button cancel ' + (confirm.cancel.class_ || '') + '">' + (confirm.cancel.label || 'Cancel') + '</a>&nbsp;';
						}
						if(confirm.ok) {
							html = html + '<a href="#" class="button ok ' + (confirm.ok.class_ || '') + '">' + (confirm.ok.label || 'Ok') + '</a>';
						}
						html = html + '</div>' +
							'</div>';
						var dlg = $(html);
						$('body').append(dlg);
						dlg.find('a.cancel').on('click', function(ev) {
							ev.preventDefault();
							dlg.foundation().foundation('reveal', 'close');
						});
						dlg.find('a.ok').on('click', function(ev) {
							ev.preventDefault();
							var frm = $('<form action="' + component.attr('href') + '" method="post"></form>');
							$('body').append(frm);
							frm.submit();
						});
						dlg.foundation().foundation('reveal', 'open');
						$(document).on('closed.fndtn.reveal', '[data-reveal]', function () {
							dlg.remove();
						});
					} else {
						var frm = $('<form action="' + component.attr('href') + '" method="post"></form>');
						$('body').append(frm);
						frm.submit();
					}
				});
			});
		}
	};
		
	$.fn.postLink = function(method) {
	    if(methods[method]) {
	   		return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
	    } else if(typeof method === 'object' || !method) {
	   		return methods.init.apply(this, arguments);
	   	} else {
	   		$.error('Method ' +  method + ' does not exist on jQuery.postLink');
	   	}
	};
}(jQuery));

(function ($) {
	/**
	 * The fancyFlash jQuery plugin provides a more fancy display of the flash messages.
	 */
	var methods = {
		init: function(options) {
			return this.each(function() {
				var component = $(this);
				component.css('position', 'absolute').css('z-index', '1000').css('width', '30em');
				component.find('.column, .columns').css('padding-right', '5px');
				component.position({
					my: 'right top+5px',
					at: 'right bottom',
					of: $('nav.top-bar')
				});
				$(window).on('resize', function() {
					component.position({
						my: 'right top+5px',
						at: 'right bottom',
						of: $('nav.top-bar')
					});
				});
			});
		}
	};
		
	$.fn.fancyFlash = function(method) {
	    if(methods[method]) {
	   		return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
	    } else if(typeof method === 'object' || !method) {
	   		return methods.init.apply(this, arguments);
	   	} else {
	   		$.error('Method ' +  method + ' does not exist on jQuery.fancyFlash');
	   	}
	};
}(jQuery));
