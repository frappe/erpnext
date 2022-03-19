// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Subcontracting Order', {
	setup: function (frm) {
		frm.set_query('purchase_order', () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 'Yes'
				}
			};
		});

		frm.set_query("item_code", "service_items", () => {
			return {
				filters: {
					is_stock_item: 0
				}
			};
		});

		frm.set_query("item_code", "fg_items", () => {
			return {
				filters: {
					is_sub_contracted_item: 1
				}
			};
		});

		frm.set_query("bom", "fg_items", function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					item: d.item_code,
					is_active: 1
				}
			};
		});
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1) {
			cur_frm.add_custom_button(__('Subcontracting Receipt'), make_subcontracting_receipt, __('Create'));
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		frm.trigger('get_materials_from_supplier');
	},

	purchase_order: function (frm) {
		if (!frm.doc.purchase_order) {
			frm.set_value("service_items", null);
		}
	},

	get_materials_from_supplier: function (frm) {
		let fg_items = [];

		if (frm.doc.supplied_items && (frm.doc.per_received == 100 || frm.doc.status === 'Completed')) {
			frm.doc.supplied_items.forEach(d => {
				if (d.total_supplied_qty && d.total_supplied_qty != d.consumed_qty) {
					fg_items.push(d.name)
				}
			});
		}

		if (fg_items && fg_items.length) {
			frm.add_custom_button(__('Return of Components'), () => {
				frm.call({
					method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.get_materials_from_supplier',
					freeze: true,
					freeze_message: __('Creating Stock Entry...'),
					args: { subcontracting_order: frm.doc.name, sco_details: fg_items },
					callback: function (r) {
						if (r && r.message) {
							const doc = frappe.model.sync(r.message);
							frappe.set_route("Form", doc[0].doctype, doc[0].name);
						}
					}
				});
			}, __('Create'));
		}
	}
});

frappe.ui.form.on('Subcontracting Order Service Item', {
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

frappe.ui.form.on('Subcontracting Order Finished Good Item', {
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

frappe.ui.form.on('Subcontracting Order Supplied Item', {
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

let make_subcontracting_receipt = () => {
	frappe.model.open_mapped_doc({
		method: "erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
		frm: cur_frm,
		freeze_message: __("Creating Subcontracting Receipt ...")
	})
}

let calculate_amount = (frm, cdt, cdn) => {
	let item = frappe.get_doc(cdt, cdn);
	if (item.item_code)
		item.amount = item.rate * item.qty;
	else
		item.rate = item.amount = 0.0;
	frm.refresh_fields();
}