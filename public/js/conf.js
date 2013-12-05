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
		var d = new wn.ui.Dialog({title: wn._('About ERPNext')})
	
		$(d.body).html(repl("<div>\
		<p>"+wn._("ERPNext is an open-source web based ERP made by Web Notes Technologies Pvt Ltd.\
		to provide an integrated tool to manage most processes in a small organization.\
		For more information about Web Notes, or to buy hosting servies, go to ")+
		"<a href='https://erpnext.com'>https://erpnext.com</a>.</p>\
		<p>"+wn._("To report an issue, go to ")+"<a href='https://github.com/webnotes/erpnext/issues'>GitHub Issues</a></p>\
		<hr>\
		<p><a href='http://www.gnu.org/copyleft/gpl.html'>License: GNU General Public License Version 3</a></p>\
		</div>", wn.app));
	
		wn.ui.misc.about_dialog = d;		
	}
	
	wn.ui.misc.about_dialog.show();
}
