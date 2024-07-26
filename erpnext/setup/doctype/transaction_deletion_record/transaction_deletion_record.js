// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transaction Deletion Record", {
	onload: function (frm) {
		if (frm.doc.docstatus == 0) {
			let doctypes_to_be_ignored_array;
			frappe.call({
				method: "erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.get_doctypes_to_be_ignored",
				callback: function (r) {
					doctypes_to_be_ignored_array = r.message;
					populate_doctypes_to_be_ignored(doctypes_to_be_ignored_array, frm);
					frm.refresh_field("doctypes_to_be_ignored");
				},
			});
		}
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1 && ["Queued", "Failed"].find((x) => x == frm.doc.status)) {
			let execute_btn = frm.doc.status == "Queued" ? __("Start Deletion") : __("Retry");

			frm.add_custom_button(execute_btn, () => {
				// Entry point for chain of events
				frm.call({
					method: "start_deletion_tasks",
					doc: frm.doc,
				});
			});
		}
	},
});

function populate_doctypes_to_be_ignored(doctypes_to_be_ignored_array, frm) {
	if (frm.doc.doctypes_to_be_ignored.length === 0) {
		var i;
		for (i = 0; i < doctypes_to_be_ignored_array.length; i++) {
			frm.add_child("doctypes_to_be_ignored", {
				doctype_name: doctypes_to_be_ignored_array[i],
			});
		}
	}
}
