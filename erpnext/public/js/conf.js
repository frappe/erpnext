// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	frappe.app.name = "ERPNext";

	$('.navbar-home').html('ERPNext');

	$('[data-link="docs"]').attr("href", "https://erpnext.com/user-guide")
});

// doctypes created via tree
frappe.create_routes["Customer Group"] = "Sales Browser/Customer Group";
frappe.create_routes["Territory"] = "Sales Browser/Territory";
frappe.create_routes["Item Group"] = "Sales Browser/Item Group";
frappe.create_routes["Sales Person"] = "Sales Browser/Sales Person";
frappe.create_routes["Account"] = "Accounts Browser/Account";
frappe.create_routes["Cost Center"] = "Accounts Browser/Cost Center";
