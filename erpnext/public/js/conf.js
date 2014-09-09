// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	frappe.app.name = "ERPNext";

	$('.navbar-brand').html('<i class="icon-home"></i>')
	.attr("title", "Home")
	.addClass("navbar-icon-home")
	.css({
		"max-width": "200px",
		"text-overflow": "ellipsis",
		"white-space": "nowrap"
	});

	$('[data-link="docs"]').attr("href", "https://erpnext.com/user-guide")
});
