// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Reservation Entry", {
	refresh(frm) {
		// Hide "Amend" button on cancelled document
		if (frm.doc.docstatus == 2) {
			frm.page.btn_primary.hide()
		}

		frm.trigger("toggle_read_only_fields");
	},

	has_serial_no(frm) {
		frm.trigger("toggle_read_only_fields");
	},

	has_batch_no(frm) {
		frm.trigger("toggle_read_only_fields");
	},

	toggle_read_only_fields(frm) {
		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"serial_no", "read_only", !frm.doc.has_serial_no
		);

		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"batch_no", "read_only", !frm.doc.has_batch_no
		);
	},
});
