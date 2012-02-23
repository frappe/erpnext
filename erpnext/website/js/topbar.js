// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

wn.provide('erpnext.navbar');

/*
<li class="dropdown">\
	<a class="dropdown-toggle" href="#" onclick="return false;"></a>\
	<ul class="dropdown-menu" id="toolbar-user">\
	</ul>\
</li>\
*/

erpnext.navbar.navbar = Class.extend({
	init: function() {
		this.make();
		$('.brand').html(wn.boot.website_settings.brand_html);
		this.make_items();
		$('.dropdown-toggle').dropdown();
	},
	make: function() {
		$('header').append('<div class="navbar navbar-fixed-top">\
			<div class="navbar-inner">\
			<div class="container">\
				<a class="brand">[brand]</a>\
				<ul class="nav">\
				</ul>\
				<img src="lib/images/ui/spinner.gif" id="spinner"/>\
				<ul class="nav pull-right">\
					<li><a href="#!Login Page">Login</a></li>\
				</ul>\
			</div>\
			</div>\
			</div>');
		$('.brand').attr('href', '#!' + (wn.boot.website_settings.home_page || 'Login Page'))
	},
	make_items: function() {
		var items = wn.boot.website_menus;
		
		// parent labels
		for(var i=0;i<items.length;i++) {
			var item = items[i];
			if(!item.parent_label && item.parentfield=='top_bar_items') {
				item.route = item.url || item.custom_page;
				$('header .nav:first').append(repl('<li data-label="%(label)s">\
					<a href="#!%(route)s">%(label)s</a></li>', item))
			}
		}
		
		// child labels
		for(var i=0;i<items.length;i++) {
			var item = items[i];
			if(item.parent_label && item.parentfield=='top_bar_items') {
				// check if parent label has class "dropdown"
				$parent_li = $(repl('header li[data-label="%(parent_label)s"]', item));
				if(!$parent_li.hasClass('dropdown')) {
					$parent_li.addClass('dropdown');
					$parent_li.find('a:first').addClass('dropdown-toggle')
						.attr('data-toggle', 'dropdown')
						.attr('href', '')
						.append('<b class="caret"></b>')
						.click(function() {
							return false;
						});
					$parent_li.append('<ul class="dropdown-menu"></ul>');
				}
				item.route = item.url || item.custom_page;
				$parent_li.find('.dropdown-menu').append(repl('<li data-label="%(label)s">\
					<a href="#!%(route)s">%(label)s</a></li>', item))
			}
		}
	}
});


// footer
erpnext.Footer = Class.extend({
	init: function() {
		$('footer').html(repl('<div class="web-footer">\
			<div class="web-footer-menu"><ul></ul></div>\
			<div class="web-footer-address">%(address)s</div>\
			<div class="web-footer-copyright">&copy; %(copyright)s</div>\
			<div class="web-footer-powered">Powered by \
				<a href="https://erpnext.com">erpnext.com</a></div>\
		</div>', wn.boot.website_settings));
		this.make_items();
	},
	make_items: function() {
		var items = wn.boot.website_menus
		for(var i=0;i<items.length;i++) {
			var item = items[i];
			if(!item.parent_label && item.parentfield=='footer_items') {
				item.route = item.url || item.custom_page;
				$('.web-footer-menu ul').append(repl('<li><a href="#!%(route)s" \
					data-label="%(label)s">%(label)s</a></li>', item))
			}
		}
	}
});

$(document).bind('startup', function() {
	erpnext.footer = new erpnext.Footer();
	erpnext.navbar.navbar = new erpnext.navbar.navbar();	
})
