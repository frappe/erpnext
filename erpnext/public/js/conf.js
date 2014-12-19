// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	frappe.app.name = "ERPNext";

	$('.navbar-brand').html('ERPNext');

	$('[data-link="docs"]').attr("href", "https://erpnext.com/user-guide")
});
