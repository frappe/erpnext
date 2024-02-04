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
					frm.fields_dict["doctypes_to_be_ignored"].grid.set_column_disp("no_of_docs", false);
					frm.refresh_field("doctypes_to_be_ignored");
				},
			});
		}


		frm.get_field('doctypes_to_be_ignored').grid.cannot_add_rows = true;
		frm.fields_dict['doctypes_to_be_ignored'].grid.set_column_disp('no_of_docs', false);
		frm.fields_dict['doctypes_to_be_ignored'].grid.set_column_disp('done', false);
		frm.refresh_field('doctypes_to_be_ignored');

		frm.get_field('doctypes').grid.cannot_add_rows = true;
		frm.fields_dict['doctypes'].grid.set_column_disp('no_of_docs', true);
		frm.refresh_field('doctypes');
	},

	refresh: function (frm) {
		frm.fields_dict["doctypes_to_be_ignored"].grid.set_column_disp("no_of_docs", false);
		frm.refresh_field("doctypes_to_be_ignored");

		if (frm.doc.docstatus==1 && ['Queued', 'Failed'].find(x => x == frm.doc.status)) {
			let execute_btn = __("Start / Resume")

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: 'start_deletion_process',
					doc: frm.doc
				});
			});
		}

		if (frm.doc.docstatus==1 && ['Queued', 'Failed'].find(x => x == frm.doc.status)) {
			let execute_btn = __("Start Chain of Events")

			frm.add_custom_button(execute_btn, () => {
				frm.call({
					method: 'delete_bins',
					doc: frm.doc
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
