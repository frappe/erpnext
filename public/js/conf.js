// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.provide('erpnext');

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	wn.app.name = "ERPNext";
	
	var brand = ($("<div></div>").append(wn.boot.website_settings.brand_html).text() || 'erpnext');
	$('.navbar-brand').html('<div style="display: inline-block;">\
			<object type="image/svg+xml" data="app/images/splash.svg" class="toolbar-splash"></object>\
		</div>' + brand)
	.attr("title", brand)
	.addClass("navbar-icon-home")
	.css({
		"max-width": "200px",
		"overflow": "hidden",
		"text-overflow": "ellipsis",
		"white-space": "nowrap"
	});
});

wn.provide('wn.ui.misc');
wn.ui.misc.about = function() {
	if(!wn.ui.misc.about_dialog) {
		var d = new wn.ui.Dialog({title: wn._('About')})
	
		$(d.body).html(repl("<div>\
		<h2>ERPNext</h2>  \
		<p><strong>v" + wn.boot.app_version + "</strong></p>\
		<p>"+wn._("An open source ERP made for the web.</p>") +
		"<p>"+wn._("To report an issue, go to ")+"<a href='https://github.com/webnotes/erpnext/issues'>GitHub Issues</a></p> \
		<p><a href='http://erpnext.org' target='_blank'>http://erpnext.org</a>.</p>\
		<p><a href='http://www.gnu.org/copyleft/gpl.html'>License: GNU General Public License Version 3</a></p>\
		<hr>\
		<p>&copy; 2014 Web Notes Technologies Pvt. Ltd and contributers </p> \
		</div>", wn.app));
	
		wn.ui.misc.about_dialog = d;		
	}
	
	wn.ui.misc.about_dialog.show();
}
