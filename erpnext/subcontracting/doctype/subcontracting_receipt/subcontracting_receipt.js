// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontracting Receipt', {
	setup: (frm) => {
		frm.set_query('subcontracting_order', () => {
			return {
				filters: {
					docstatus: 1,
				}
			};
		});

		frm.set_query('item_code', 'service_items', () => {
			return {
				filters: {
					is_stock_item: 0
				}
			};
		});

		frm.set_query('item_code', 'fg_items', () => {
			return {
				filters: {
					is_sub_contracted_item: 1
				}
			};
		});

		frm.set_query('bom', 'fg_items', (doc, cdt, cdn) => {
			let d = locals[cdt][cdn];
			return {
				filters: {
					item: d.item_code,
					is_active: 1
				}
			};
		});
	},

	subcontracting_order: (frm) => {
		if (frm.doc.subcontracting_order) {
			frappe.call({
				method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt',
				args: {
					source_name: frm.doc.subcontracting_order,
				},
				freeze_message: __('Mapping Subcontracting Receipt ...'),
				callback: (r) => {
					if (!r.exc) {
						var fields_to_skip = ['owner', 'docstatus', 'idx', 'doctype', '__islocal', '__onload', '__unsaved'];
						var fields_to_map = Object.keys(r.message).filter(n => !fields_to_skip.includes(n));
						$.each(fields_to_map, (i, field) => {
							frm.set_value(field, r.message[field]);
						});
					};
				}
			});
		}
	},
});

frappe.ui.form.on('Subcontracting Receipt Service Item', {
	item_code(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	qty(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
});

frappe.ui.form.on('Subcontracting Receipt Finished Good Item', {
	item_code(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	qty(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
});

frappe.ui.form.on('Subcontracting Receipt Supplied Item', {
	item_code(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	qty(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
	rate(frm, cdt, cdn) {
		calculate_amount(frm, cdt, cdn);
	},
});

let calculate_amount = (frm, cdt, cdn) => {
	let item = frappe.get_doc(cdt, cdn);
	if (item.item_code)
		item.amount = item.rate * item.qty;
	else
		item.rate = item.amount = 0.0;
	frm.refresh_fields();
}
