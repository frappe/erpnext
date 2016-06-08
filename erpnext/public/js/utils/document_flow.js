// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

// for module flow

$.extend(frappe.document_flow, {
	"Selling": {
		"Sales Order": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Journal Entry"],
		"Quotation": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Journal Entry"]
	},
	"Accounts": {
		"Sales Invoice": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Journal Entry"],
		"Purchase Invoice": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Journal Entry"]
	},
	"Buying": {
		"Purchase Order": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Journal Entry"],
		"Supplier Quotation": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Journal Entry"]
	},
	"Stock": {
		"Delivery Note": ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice", "Journal Entry"],
		"Purchase Receipt": ["Supplier Quotation", "Purchase Order", "Purchase Receipt",
			"Purchase Invoice", "Journal Entry"]
	}
});
