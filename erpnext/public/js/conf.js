// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	frappe.app.name = "ERPNext";

	frappe.help_feedback_link = '<p><a class="text-muted" \
		href="https://discuss.erpnext.com">Feedback</a></p>'


	$('.navbar-home').html('<img class="erpnext-icon" src="/assets/erpnext/images/erp-icon.svg" />');

	$('[data-link="docs"]').attr("href", "https://manual.erpnext.com")
});

// doctypes created via tree
$.extend(frappe.create_routes, {
	"Customer Group": "Sales Browser/Customer Group",
	"Territory": "Sales Browser/Territory",
	"Item Group": "Sales Browser/Item Group",
	"Sales Person": "Sales Browser/Sales Person",
	"Account": "Accounts Browser/Account",
	"Cost Center": "Accounts Browser/Cost Center"
});

// preferred modules for breadcrumbs
$.extend(frappe.breadcrumbs.preferred, {
	"Item Group": "Stock",
	"Customer Group": "Selling",
	"Supplier Type": "Buying",
	"Territory": "Selling",
	"Sales Person": "Selling",
	"Sales Partner": "Selling",
	"Brand": "Selling"
});
