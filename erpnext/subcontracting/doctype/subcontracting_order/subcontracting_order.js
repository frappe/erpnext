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
	},

	purchase_order: function (frm) {
		if (!frm.doc.purchase_order) {
			frm.set_value("service_items", null);
		}
	},
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

let make_subcontracting_receipt = () => {
	frappe.model.open_mapped_doc({
		method: "erpnext.buying.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
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