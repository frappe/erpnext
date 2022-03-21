// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('erpnext.accounts.dimensions');

frappe.ui.form.on('Subcontracting Order', {
	setup: function (frm) {
		frm.set_indicator_formatter('item_code',
			function (doc) { return (doc.qty <= doc.received_qty) ? 'green' : 'orange' });

		frm.set_query('purchase_order', () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 'Yes'
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

		frm.set_query('expense_account', 'fg_items', function () {
			return {
				query: 'erpnext.controllers.queries.get_expense_account',
				filters: { 'company': frm.doc.company }
			}
		});

		frm.set_query('bom', 'fg_items', function (doc, cdt, cdn) {
			let d = locals[cdt][cdn];
			return {
				filters: {
					item: d.item_code,
					is_active: 1
				}
			};
		});

		frm.set_query('reserve_warehouse', 'supplied_items', function () {
			return {
				filters: {
					'company': frm.doc.company,
					'name': ['!=', frm.doc.supplier_warehouse],
					'is_group': 0
				}
			}
		});
	},

	onload: function (frm) {
		set_schedule_date(frm);
		if (!frm.doc.transaction_date) {
			frm.set_value('transaction_date', frappe.datetime.get_today())
		}

		erpnext.queries.setup_queries(frm, 'Warehouse', function () {
			return erpnext.queries.warehouse(frm.doc);
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
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
			frm.set_value('service_items', null);
		}
	},

	company: function (frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
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
							frappe.set_route('Form', doc[0].doctype, doc[0].name);
						}
					}
				});
			}, __('Create'));
		}
	},

	apply_tds: function (frm) {
		if (!frm.doc.apply_tds) {
			frm.set_value('tax_withholding_category', '');
		} else {
			frm.set_value('tax_withholding_category', frm.supplier_tds);
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

frappe.ui.form.on('Subcontracting Order Finished Good Item', {
	schedule_date: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if (!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, 'fg_items', 'schedule_date');
			} else {
				set_schedule_date(frm);
			}
		}
	},

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

cur_frm.fields_dict['fg_items'].grid.get_field('bom').get_query = function (doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: [
			['BOM', 'item', '=', d.item_code],
			['BOM', 'is_active', '=', '1'],
			['BOM', 'docstatus', '=', '1'],
			['BOM', 'company', '=', doc.company]
		]
	}
}

let set_schedule_date = (frm) => {
	if (frm.doc.schedule_date) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, 'fg_items', 'schedule_date');
	}
}

let make_subcontracting_receipt = () => {
	frappe.model.open_mapped_doc({
		method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt',
		frm: cur_frm,
		freeze_message: __('Creating Subcontracting Receipt ...')
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