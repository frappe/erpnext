// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Consolidation Transaction', {
	refresh: function(frm) {
		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__("Make Adjustment Entry"),
			()=>{
				console.log(frm.doc.name)
				frappe.model.open_mapped_doc({
				method: "erpnext.accounts.doctype.consolidation_transaction.consolidation_transaction.make_adjustment_entry",
				frm: frm
				});
			})
			frm.add_custom_button(__('Consolidation Report'), function () {
				frappe.route_options = {
					"from_date": frm.doc.from_date,
					"to_date": frm.doc.to_date
				};
				frappe.set_route("query-report", "Consolidation Report");
			}, "fa fa-table");
		}
	},
});
