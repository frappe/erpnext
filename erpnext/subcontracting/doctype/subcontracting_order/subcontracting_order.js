// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('erpnext.buying');

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

		if (frm.doc.supplied_items && (frm.doc.per_received == 100)) {
			frm.doc.supplied_items.forEach(d => {
				if (d.total_supplied_qty && d.total_supplied_qty != d.consumed_qty) {
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
			if (doc.status != 'Completed') {
				if (flt(doc.per_received) < 100) {
					cur_frm.add_custom_button(__('Subcontracting Receipt'), this.make_subcontracting_receipt, __('Create'));
					if (me.has_unsupplied_items()) {
						cur_frm.add_custom_button(__('Material to Supplier'),
							() => {
								me.make_stock_entry();
							}, __('Transfer'));
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

	make_stock_entry() {
		var items = $.map(cur_frm.doc.items, (d) => d.bom ? d.item_code : false);
		var me = this;

		if (items.length >= 1) {
			me.raw_material_data = [];
			me.show_dialog = 1;
			let title = __('Transfer Material to Supplier');
			let fields = [
				{ fieldtype: 'Section Break', label: __('Raw Materials') },
				{
					fieldname: 'sub_con_rm_items', fieldtype: 'Table', label: __('Items'),
					fields: [
						{
							fieldtype: 'Data',
							fieldname: 'item_code',
							label: __('Item'),
							read_only: 1,
							in_list_view: 1
						},
						{
							fieldtype: 'Data',
							fieldname: 'rm_item_code',
							label: __('Raw Material'),
							read_only: 1,
							in_list_view: 1
						},
						{
							fieldtype: 'Float',
							read_only: 1,
							fieldname: 'qty',
							label: __('Quantity'),
							in_list_view: 1
						},
						{
							fieldtype: 'Data',
							read_only: 1,
							fieldname: 'warehouse',
							label: __('Reserve Warehouse'),
							in_list_view: 1
						},
						{
							fieldtype: 'Float',
							read_only: 1,
							fieldname: 'rate',
							label: __('Rate'),
							hidden: 1
						},
						{
							fieldtype: 'Float',
							read_only: 1,
							fieldname: 'amount',
							label: __('Amount'),
							hidden: 1
						},
						{
							fieldtype: 'Link',
							read_only: 1,
							fieldname: 'uom',
							label: __('UOM'),
							hidden: 1
						}
					],
					data: me.raw_material_data,
					get_data: () => me.raw_material_data
				}
			];

			me.dialog = new frappe.ui.Dialog({
				title: title, fields: fields
			});

			if (me.frm.doc['supplied_items']) {
				me.frm.doc['supplied_items'].forEach((item) => {
					if (item.rm_item_code && item.main_item_code && item.required_qty - item.supplied_qty != 0) {
						me.raw_material_data.push({
							'name': item.name,
							'item_code': item.main_item_code,
							'rm_item_code': item.rm_item_code,
							'item_name': item.rm_item_code,
							'qty': item.required_qty - item.supplied_qty,
							'warehouse': item.reserve_warehouse,
							'rate': item.rate,
							'amount': item.amount,
							'stock_uom': item.stock_uom
						});
						me.dialog.fields_dict.sub_con_rm_items.grid.refresh();
					}
				});
			}

			me.dialog.get_field('sub_con_rm_items').check_all_rows();

			me.dialog.show();
			this.dialog.set_primary_action(__('Transfer'), () => {
				me.values = me.dialog.get_values();
				if (me.values) {
					me.values.sub_con_rm_items.map((row, i) => {
						if (!row.item_code || !row.rm_item_code || !row.warehouse || !row.qty || row.qty === 0) {
							let row_id = i + 1;
							frappe.throw(__('Item Code, warehouse and quantity are required on row {0}', [row_id]));
						}
					});
					me.make_rm_stock_entry(me.dialog.fields_dict.sub_con_rm_items.grid.get_selected_children());
					me.dialog.hide();
				}
			});
		}

		me.dialog.get_close_btn().on('click', () => {
			me.dialog.hide();
		});
	}

	has_unsupplied_items() {
		return this.frm.doc['supplied_items'].some(item => item.required_qty > item.supplied_qty);
	}

	make_subcontracting_receipt() {
		frappe.model.open_mapped_doc({
			method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt',
			frm: cur_frm,
			freeze_message: __('Creating Subcontracting Receipt ...')
		});
	}

	make_rm_stock_entry(rm_items) {
		frappe.call({
			method: 'erpnext.controllers.subcontracting_controller.make_rm_stock_entry',
			args: {
				subcontract_order: cur_frm.doc.name,
				rm_items: rm_items,
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