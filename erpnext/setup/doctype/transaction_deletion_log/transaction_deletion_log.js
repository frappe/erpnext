// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transaction Deletion Log', {
	refresh: function(frm) {
		let doctypes_to_be_ignored = ["Account", "Cost Center", "Warehouse", "Budget",
			"Party Account", "Employee", "Sales Taxes and Charges Template",
			"Purchase Taxes and Charges Template", "POS Profile", "BOM",
			"Company", "Bank Account", "Item Tax Template", "Mode Of Payment",
			"Item Default", "Customer", "Supplier", "GST Account"]

		var i;
		for (i = 0; i < doctypes_to_be_ignored.length; i++) { 
			frm.add_child('customisable_doctypes', {
					doctype_name : doctypes_to_be_ignored[i]
				});
		}
		
		frm.get_field('customisable_doctypes').grid.cannot_add_rows = true;
		// frm.get_field('customisable_doctypes').grid.only_sortable();
		frm.refresh_field('customisable_doctypes');
	}
});