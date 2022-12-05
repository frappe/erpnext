// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Serial and Batch Bundle', {
	setup(frm) {
		frm.trigger('set_queries');
	},

	refresh(frm) {
		frm.trigger('toggle_fields');
	},

	warehouse(frm) {
		if (frm.doc.warehouse) {
			frm.call({
				method: "set_warehouse",
				doc: frm.doc,
				callback(r) {
					refresh_field("ledgers");
				}
			})
		}
	},

	has_serial_no(frm) {
		frm.trigger('toggle_fields');
	},

	has_batch_no(frm) {
		frm.trigger('toggle_fields');
	},

	toggle_fields(frm) {
		frm.fields_dict.ledgers.grid.update_docfield_property(
			'serial_no', 'read_only', !frm.doc.has_serial_no
		);

		frm.fields_dict.ledgers.grid.update_docfield_property(
			'batch_no', 'read_only', !frm.doc.has_batch_no
		);
	},

	set_queries(frm) {
		frm.set_query('item_code', () => {
			return {
				query: 'erpnext.stock.doctype.serial_and_batch_bundle.serial_and_batch_bundle.item_query',
			};
		});

		frm.set_query('voucher_type', () => {
			return {
				filters: {
					'istable': 0,
					'issingle': 0,
					'is_submittable': 1,
				}
			};
		});

		frm.set_query('voucher_no', () => {
			return {
				filters: {
					'docstatus': ["!=", 2],
				}
			};
		});

		frm.set_query('warehouse', () => {
			return {
				filters: {
					'is_group': 0,
					'company': frm.doc.company,
				}
			};
		});

		frm.set_query('serial_no', 'ledgers', () => {
			return {
				filters: {
					item_code: frm.doc.item_code,
				}
			};
		});

		frm.set_query('batch_no', 'ledgers', () => {
			return {
				filters: {
					item: frm.doc.item_code,
				}
			};
		});

		frm.set_query('warehouse', 'ledgers', () => {
			return {
				filters: {
					company: frm.doc.company,
				}
			};
		});
	}
});


frappe.ui.form.on("Serial and Batch Ledger", {
	ledgers_add(frm, cdt, cdn) {
		if (frm.doc.warehouse) {
			locals[cdt][cdn].warehouse = frm.doc.warehouse;
		}
	},
})