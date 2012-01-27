wn.provide('erpnext.topbar');
wn.require('lib/css/bootstrap/bootstrap-topbar.css');
wn.require('lib/js/bootstrap/bootstrap-dropdown.js');

/*
<li class="dropdown">\
	<a class="dropdown-toggle" href="#" onclick="return false;"></a>\
	<ul class="dropdown-menu" id="toolbar-user">\
	</ul>\
</li>\
*/

erpnext.topbar.TopBar = Class.extend({
	init: function() {
		this.make();
		$('.brand').html(wn.boot.topbar.brand_html);
		this.make_items();
	},
	make: function() {
		$('header').append('<div class="topbar">\
			<div class="topbar-inner">\
			<div class="container">\
				<a class="brand" href="#!home">[brand]</a>\
				<ul class="nav">\
				</ul>\
				<img src="lib/images/ui/spinner.gif" id="spinner"/>\
				<ul class="nav secondary-nav">\
					<li><a href="#!Login Page">Login</a></li>\
				</ul>\
			</div>\
			</div>\
			</div>');
	},
	make_items: function() {
		var items = wn.boot.topbaritems
		for(var i=0;i<items.length;i++) {
			var item = items[i];
			if(!item.parent_label) {
				item.route = item.std_page.toLowerCase();
				$('header .nav:first').append(repl('<li><a href="#!%(route)s" \
					data-label="%(label)s">%(label)s</a></li>', item))
			}
		}
	}
});

erpnext.topbar.topbar = new erpnext.topbar.TopBar();