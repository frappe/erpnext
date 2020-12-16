// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Internal Ticket', {
	refresh: function(frm) {
		frm.add_custom_button(__("Task"), function () {
			frappe.model.open_mapped_doc({
				method: "erpnext.hr.doctype.internal_ticket.internal_ticket.make_task",
				frm: frm,
			});
		}, __("Create"));
	}
});
