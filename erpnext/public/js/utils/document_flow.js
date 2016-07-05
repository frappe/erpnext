// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

// for module flow

$.extend(frappe.document_flow, {
	"Selling": {
		"Sales Order": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Payment Entry"],
		"Quotation": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Payment Entry"]
	},
	"Accounts": {
		"Sales Invoice": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Payment Entry"],
		"Purchase Invoice": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Payment Entry"]
	},
	"Buying": {
		"Purchase Order": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Payment Entry"],
		"Supplier Quotation": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Payment Entry"]
	},
	"Stock": {
		"Delivery Note": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Payment Entry"],
		"Purchase Receipt": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Payment Entry"]
	}
});
