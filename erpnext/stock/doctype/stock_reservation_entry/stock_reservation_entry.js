// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stock Reservation Entry", {
	refresh(frm) {
		frm.trigger("set_queries");
		frm.trigger("toggle_read_only_fields");
		frm.trigger("hide_rate_related_fields");
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
					is_group: 0,
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("serial_no", "sb_entries", function (doc, cdt, cdn) {
			var selected_serial_nos = doc.sb_entries.map((row) => {
				return row.serial_no;
			});
			var row = locals[cdt][cdn];
			return {
				filters: {
					item_code: doc.item_code,
					warehouse: row.warehouse,
					status: "Active",
					name: ["not in", selected_serial_nos],
				},
			};
		});

		frm.set_query("batch_no", "sb_entries", function (doc, cdt, cdn) {
			let filters = {
				item: doc.item_code,
				batch_qty: [">", 0],
				disabled: 0,
			};

			if (!doc.has_serial_no) {
				var selected_batch_nos = doc.sb_entries.map((row) => {
					return row.batch_no;
				});

				filters.name = ["not in", selected_batch_nos];
			}

			return { filters: filters };
		});
	},

	toggle_read_only_fields(frm) {
		if (frm.doc.has_serial_no) {
			frm.doc.sb_entries.forEach((row) => {
				if (row.qty !== 1) {
					frappe.model.set_value(row.doctype, row.name, "qty", 1);
				}
			});
		}

		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"serial_no",
			"read_only",
			!frm.doc.has_serial_no
		);

		frm.fields_dict.sb_entries.grid.update_docfield_property(
			"batch_no",
			"read_only",
			!frm.doc.has_batch_no
		);

		// Qty will always be 1 for Serial No.
		frm.fields_dict.sb_entries.grid.update_docfield_property("qty", "read_only", frm.doc.has_serial_no);

		frm.set_df_property(
			"sb_entries",
			"allow_on_submit",
			frm.doc.from_voucher_type == "Pick List" ? 0 : 1
		);
	},

	hide_rate_related_fields(frm) {
		["incoming_rate", "outgoing_rate", "stock_value_difference", "is_outward", "stock_queue"].forEach(
			(field) => {
				frm.fields_dict.sb_entries.grid.update_docfield_property(field, "hidden", 1);
			}
		);
	},

	hide_primary_action_button(frm) {
		// Hide 'Amend' button on cancelled document
		if (frm.doc.docstatus == 2) {
			frm.page.btn_primary.hide();
		}
	},

	make_sb_entries_warehouse_read_only(frm) {
		frm.fields_dict.sb_entries.grid.update_docfield_property("warehouse", "read_only", 1);
	},
});

frappe.ui.form.on("Serial and Batch Entry", {
	sb_entries_add(frm, cdt, cdn) {
		if (frm.doc.warehouse) {
			frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.warehouse);
		}
	},
});
