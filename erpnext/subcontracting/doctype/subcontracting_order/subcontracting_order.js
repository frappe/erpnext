// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('erpnext.buying');

{% include 'erpnext/stock/landed_taxes_and_charges_common.js' %};

frappe.ui.form.on('Subcontracting Order', {
	setup: (frm) => {
		frm.get_field("items").grid.cannot_add_rows = true;
		frm.get_field("items").grid.only_sortable();

		frm.set_indicator_formatter('item_code',
			(doc) => (doc.qty <= doc.received_qty) ? 'green' : 'orange');

		frm.set_query('supplier_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query('purchase_order', () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 1,
					is_old_subcontracting_flow: 0
				}
			};
		});

		frm.set_query('set_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query('warehouse', 'items', () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0
			}
		}));

		frm.set_query('expense_account', 'items', () => ({
			query: 'erpnext.controllers.queries.get_expense_account',
			filters: {
				company: frm.doc.company
			}
		}));

		frm.set_query('bom', 'items', (doc, cdt, cdn) => {
			let d = locals[cdt][cdn];
			return {
				filters: {
					item: d.item_code,
					is_active: 1,
					docstatus: 1,
					company: frm.doc.company
				}
			};
		});

		frm.set_query('set_reserve_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					name: ['!=', frm.doc.supplier_warehouse],
					is_group: 0
				}
			};
		});
	},

	onload: (frm) => {
		if (!frm.doc.transaction_date) {
			frm.set_value('transaction_date', frappe.datetime.get_today());
		}
	},

	purchase_order: (frm) => {
		frm.set_value('service_items', null);
		frm.set_value('items', null);
		frm.set_value('supplied_items', null);

		if (frm.doc.purchase_order) {
			erpnext.utils.map_current_doc({
				method: 'erpnext.buying.doctype.purchase_order.purchase_order.make_subcontracting_order',
				source_name: frm.doc.purchase_order,
				target_doc: frm,
				freeze: true,
				freeze_message: __('Mapping Subcontracting Order ...'),
			});
		}
	},

	refresh: function (frm) {
		frm.trigger('get_materials_from_supplier');
	},

	get_materials_from_supplier: function (frm) {
		let sco_rm_details = [];

		if (frm.doc.status != "Closed" && frm.doc.supplied_items) {
			frm.doc.supplied_items.forEach(d => {
				if (d.total_supplied_qty > 0 && d.total_supplied_qty != d.consumed_qty) {
					sco_rm_details.push(d.name);
				}
			});
		}

		if (sco_rm_details && sco_rm_details.length) {
			frm.add_custom_button(__('Return of Components'), () => {
				frm.call({
					method: 'erpnext.controllers.subcontracting_controller.get_materials_from_supplier',
					freeze: true,
					freeze_message: __('Creating Stock Entry'),
					args: {
						subcontract_order: frm.doc.name,
						rm_details: sco_rm_details,
						order_doctype: cur_frm.doc.doctype
					},
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

frappe.ui.form.on('Landed Cost Taxes and Charges', {
	amount: function (frm, cdt, cdn) {
		frm.events.set_base_amount(frm, cdt, cdn);
	},

	expense_account: function (frm, cdt, cdn) {
		frm.events.set_account_currency(frm, cdt, cdn);
	}
});

erpnext.buying.SubcontractingOrderController = class SubcontractingOrderController {
	setup() {
		this.frm.custom_make_buttons = {
			'Subcontracting Receipt': 'Subcontracting Receipt',
			'Stock Entry': 'Material to Supplier',
		};
	}

	refresh(doc) {
		var me = this;

		if (doc.docstatus == 1) {
			if (!['Closed', 'Completed'].includes(doc.status)) {
				if (flt(doc.per_received) < 100) {
					cur_frm.add_custom_button(__('Subcontracting Receipt'), this.make_subcontracting_receipt, __('Create'));
					if (me.has_unsupplied_items()) {
						cur_frm.add_custom_button(__('Material to Supplier'), this.make_stock_entry, __('Transfer'));
					}
				}
				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}
	}

	items_add(doc, cdt, cdn) {
		if (doc.set_warehouse) {
			var row = frappe.get_doc(cdt, cdn);
			row.warehouse = doc.set_warehouse;
		}
	}

	set_warehouse(doc) {
		this.set_warehouse_in_children(doc.items, "warehouse", doc.set_warehouse);
	}

	set_reserve_warehouse(doc) {
		this.set_warehouse_in_children(doc.supplied_items, "reserve_warehouse", doc.set_reserve_warehouse);
	}

	set_warehouse_in_children(child_table, warehouse_field, warehouse) {
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
	}

	has_unsupplied_items() {
		return this.frm.doc['supplied_items'].some(item => item.required_qty > (item.supplied_qty - item.returned_qty));
	}

	make_subcontracting_receipt() {
		frappe.model.open_mapped_doc({
			method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt',
			frm: cur_frm,
			freeze_message: __('Creating Subcontracting Receipt ...')
		});
	}

	make_stock_entry() {
		frappe.call({
			method: 'erpnext.controllers.subcontracting_controller.make_rm_stock_entry',
			args: {
				subcontract_order: cur_frm.doc.name,
				order_doctype: cur_frm.doc.doctype
			},
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route('Form', doclist[0].doctype, doclist[0].name);
			}
		});
	}
};

extend_cscript(cur_frm.cscript, new erpnext.buying.SubcontractingOrderController({ frm: cur_frm }));