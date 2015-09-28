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

frappe.desk_home_buttons.push({label:"<i class='icon-facetime-video'></i> "+ __("Learn"),
	route:"Module/Learn"})

frappe.desk_home_flows.push({
		title: __("Selling"),
		sequence: [
			{title: __("Opportunity"), route:"List/Opportunity"},
			{title: __("Quotation"), route:"List/Quotation"},
			{title: __("Sales Order"), route:"List/Sales Order"},
			{title: __("Delivery Note"), route:"List/Delivery Note"},
			{title: __("Sales Invoice"), route:"List/Sales Invoice"},
			{title: __("Payment"), route:"List/Journal Entry"},
		]
	});

frappe.desk_home_flows.push({
		title: __("Buying"),
		sequence: [
			{title: __("Material Request"), route:"List/Material Request"},
			{title: __("Supplier Quotation"), route:"List/Supplier Quotation"},
			{title: __("Purchase Order"), route:"List/Purchase Order"},
			{title: __("Purchase Receipt"), route:"List/Purchase Receipt"},
			{title: __("Purchase Invoice"), route:"List/Purchase Invoice"},
			{title: __("Payment"), route:"List/Journal Entry"},
		]
	});

frappe.desk_home_flows.push({
		title: __("Manufacturing"),
		sequence: [
			{title: __("BOM"), route:"List/BOM"},
			{title: __("Production Planning Tool"), route:"Form/Production Planning Tool"},
			{title: __("Production Order"), route:"List/Production Order"},
			{title: __("Stock Entry"), route:"List/Stock Entry"},
		]
	});
