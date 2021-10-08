// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Transaction Deletion Record', {
	onload: function(frm) {
		if (frm.doc.docstatus == 0) {
			let doctypes_to_be_ignored_array;
			frappe.call({
				method: 'erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record.get_doctypes_to_be_ignored',
				callback: function(r) {
					doctypes_to_be_ignored_array = r.message;
					populate_doctypes_to_be_ignored(doctypes_to_be_ignored_array, frm);
					frm.fields_dict['doctypes_to_be_ignored'].grid.set_column_disp('no_of_docs', false);
					frm.refresh_field('doctypes_to_be_ignored');
				}
			});
		}

		frm.get_field('doctypes_to_be_ignored').grid.cannot_add_rows = true;
		frm.fields_dict['doctypes_to_be_ignored'].grid.set_column_disp('no_of_docs', false);
		frm.refresh_field('doctypes_to_be_ignored');
	},

	refresh: function(frm) {
		frm.fields_dict['doctypes_to_be_ignored'].grid.set_column_disp('no_of_docs', false);
		frm.refresh_field('doctypes_to_be_ignored');
	}

});

function populate_doctypes_to_be_ignored(doctypes_to_be_ignored_array, frm) {
	if (!(frm.doc.doctypes_to_be_ignored)) {
		var i;
		for (i = 0; i < doctypes_to_be_ignored_array.length; i++) {
			frm.add_child('doctypes_to_be_ignored', {
				doctype_name: doctypes_to_be_ignored_array[i]
			});
		}
	}
}
