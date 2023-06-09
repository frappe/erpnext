// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Reservation Entry", {
	refresh(frm) {
		frm.trigger("set_queries");
		frm.trigger("toggle_read_only_fields");
		frm.trigger("hide_primary_action_button");
		frm.trigger("make_sb_entries_warehouse_read_only");
	},

	has_serial_no(frm) {
		frm.trigger("toggle_read_only_fields");
	},

	has_batch_no(frm) {
		frm.trigger("toggle_read_only_fields");
	},

	warehouse(frm) {
		if (frm.doc.warehouse) {
			frm.doc.sb_entries.forEach((row) => {
				frappe.model.set_value(row.doctype, row.name, "warehouse", frm.doc.warehouse);
			});
		}
	},

	set_queries(frm) {
		frm.set_query("warehouse", () => {
			return {
				filters: {
					"is_group": 0,
					"company": frm.doc.company,
				}
			};
		});
	},

	toggle_read_only_fields(frm) {
		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"serial_no", "read_only", !frm.doc.has_serial_no
		);

		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"batch_no", "read_only", !frm.doc.has_batch_no
		);
	},

	hide_primary_action_button(frm) {
		// Hide "Amend" button on cancelled document
		if (frm.doc.docstatus == 2) {
			frm.page.btn_primary.hide()
		}
	},

	make_sb_entries_warehouse_read_only(frm) {
		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"warehouse", "read_only", 1
		);
	},
});

frappe.ui.form.on("Serial and Batch Entry", {
	sb_entries_add(frm, cdt, cdn) {
		if (frm.doc.warehouse) {
			frappe.model.set_value(cdt, cdn, 'warehouse', frm.doc.warehouse);
		}
	},
});