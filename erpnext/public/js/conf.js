// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide('erpnext');

// add toolbar icon
$(document).bind('toolbar_setup', function() {
	frappe.app.name = "ERPNext";

	frappe.help_feedback_link = '<p><a class="text-muted" \
		href="https://discuss.erpnext.com">Feedback</a></p>'


	$('.navbar-home').html('<img class="erpnext-icon" src="'+
			frappe.urllib.get_base_url()+'/assets/erpnext/images/erp-icon.svg" />');

	$('[data-link="docs"]').attr("href", "https://manual.erpnext.com")
	$('[data-link="issues"]').attr("href", "https://github.com/frappe/erpnext/issues")
});

// doctypes created via tree
$.extend(frappe.create_routes, {
	"Customer Group": "Tree/Customer Group",
	"Territory": "Tree/Territory",
	"Item Group": "Tree/Item Group",
	"Sales Person": "Tree/Sales Person",
	"Account": "Tree/Account",
	"Cost Center": "Tree/Cost Center"
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
