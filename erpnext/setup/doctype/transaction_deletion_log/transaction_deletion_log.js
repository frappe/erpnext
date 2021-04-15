// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transaction Deletion Log', {
	refresh: function(frm) {
		let doctypes_to_be_ignored_list = ["Account", "Cost Center", "Warehouse", "Budget",
			"Party Account", "Employee", "Sales Taxes and Charges Template",
			"Purchase Taxes and Charges Template", "POS Profile", "BOM",
			"Company", "Bank Account", "Item Tax Template", "Mode Of Payment",
			"Item Default", "Customer", "Supplier", "GST Account"]

		if (!(frm.doc.doctypes_to_be_ignored)){
			var i;
			for (i = 0; i < doctypes_to_be_ignored_list.length; i++) { 
				frm.add_child('doctypes_to_be_ignored', {
						doctype_name : doctypes_to_be_ignored_list[i]
					});
			}
		}

		frm.get_field('doctypes_to_be_ignored').grid.cannot_add_rows = true;
		frm.fields_dict["doctypes_to_be_ignored"].grid.set_column_disp("no_of_docs", false)
		frm.refresh_field('doctypes_to_be_ignored');

		// var col= document.querySelector('[data-fieldname="no_of_docs"]');
		// console.log(col);
		// col.style.display = "none"
	}
});