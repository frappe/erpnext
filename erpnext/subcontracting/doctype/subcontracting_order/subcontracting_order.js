// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('erpnext.buying');
frappe.provide('erpnext.accounts.dimensions');
{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on('Subcontracting Order', {
	setup: (frm) => {
		frm.set_indicator_formatter('item_code',
			(doc) => (doc.qty <= doc.received_qty) ? 'green' : 'orange');

		frm.set_query('purchase_order', () => {
			return {
				filters: {
					docstatus: 1,
					is_subcontracted: 1
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

		frm.set_query('expense_account', 'fg_items', () => ({
			query: 'erpnext.controllers.queries.get_expense_account',
			filters: { 'company': frm.doc.company }
		}));

		frm.set_query('bom', 'fg_items', (doc, cdt, cdn) => {
			let d = locals[cdt][cdn];
			return {
				filters: {
					item: d.item_code,
					is_active: 1
				}
			};
		});

		frm.set_query('reserve_warehouse', 'supplied_items', () => ({
			filters: {
				'company': frm.doc.company,
				'name': ['!=', frm.doc.supplier_warehouse],
				'is_group': 0
			}
		}));
	},

	onload: (frm) => {
		set_schedule_date(frm);
		if (!frm.doc.transaction_date) {
			frm.set_value('transaction_date', frappe.datetime.get_today());
		}

		erpnext.queries.setup_queries(frm, 'Warehouse', () => erpnext.queries.warehouse(frm.doc));

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: (frm) => {
		frm.trigger('get_materials_from_supplier');
	},

	purchase_order: (frm) => {
		if (frm.doc.purchase_order) {
			erpnext.utils.map_current_doc({
				method: 'erpnext.buying.doctype.purchase_order.purchase_order.make_subcontracting_order',
				source_name: frm.doc.purchase_order,
				target_doc: frm,
				freeze_message: __('Mapping Subcontracting Order ...'),
			});
		}
		else {
			frm.set_value('service_items', null);
			frm.set_value('fg_items', null);
			frm.set_value('supplied_items', null);
		}
	},

	company: (frm) => {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	get_materials_from_supplier: (frm) => {
		let fg_items = [];

		if (frm.doc.supplied_items && (frm.doc.per_received == 100 || frm.doc.status === 'Completed')) {
			frm.doc.supplied_items.forEach(d => {
				if (d.total_supplied_qty && d.total_supplied_qty != d.consumed_qty) {
					fg_items.push(d.name);
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
					callback: (r) => {
						if (r && r.message) {
							const doc = frappe.model.sync(r.message);
							frappe.set_route('Form', doc[0].doctype, doc[0].name);
						}
					}
				});
			}, __('Create'));
		}
	},

	apply_tds: (frm) => {
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
	schedule_date: (frm, cdt, cdn) => {
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

erpnext.buying.SubcontractingOrderController = class SubcontractingOrderController {
	setup() {
		this.frm.custom_make_buttons = {
			'Subcontracting Receipt': 'Subcontracting Receipt',
			'Stock Entry': 'Material to Supplier',
		}
	}

	validate() {
		set_schedule_date(this.frm);
	}

	refresh(doc, cdt, cdn) {
		var me = this;

		if (doc.docstatus == 1) {
			if (doc.status != 'Completed') {
				if (flt(doc.per_billed) == 0) {
					cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_payment_entry, __('Create'));
				}
				if (flt(doc.per_received) < 100) {
					cur_frm.add_custom_button(__('Subcontracting Receipt'), this.make_subcontracting_receipt, __('Create'));
					if (me.has_unsupplied_items()) {
						cur_frm.add_custom_button(__('Material to Supplier'),
							() => { me.make_stock_entry(); }, __('Transfer'));
					}
				}
				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}
	}

	get_items_from_open_material_requests() {
		erpnext.utils.map_current_doc({
			method: 'erpnext.stock.doctype.material_request.material_request.make_subcontracting_order_based_on_supplier',
			args: {
				supplier: this.frm.doc.supplier
			},
			source_doctype: 'Material Request',
			source_name: this.frm.doc.supplier,
			target: this.frm,
			setters: {
				company: me.frm.doc.company
			},
			get_query_filters: {
				docstatus: ['!=', 2],
				supplier: this.frm.doc.supplier
			},
			get_query_method: 'erpnext.stock.doctype.material_request.material_request.get_material_requests_based_on_supplier'
		});
	}

	fg_items_add(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if (doc.schedule_date) {
			row.schedule_date = doc.schedule_date;
			refresh_field('schedule_date', cdn, 'fg_items');
		} else {
			this.frm.script_manager.copy_from_first_row('fg_items', row, ['schedule_date']);
		}
	}

	make_stock_entry() {
		var fg_items = $.map(cur_frm.doc.fg_items, (d) => d.bom ? d.item_code : false);
		var me = this;

		if (fg_items.length >= 1) {
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
							read_only: 1,
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
			]

			me.dialog = new frappe.ui.Dialog({
				title: title, fields: fields
			});

			if (me.frm.doc['supplied_items']) {
				me.frm.doc['supplied_items'].forEach((item, index) => {
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
				})
			}

			me.dialog.get_field('sub_con_rm_items').check_all_rows()

			me.dialog.show()
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

	fg_items_on_form_rendered() {
		set_schedule_date(this.frm);
	}

	schedule_date() {
		set_schedule_date(this.frm);
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
			method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_rm_stock_entry',
			args: {
				subcontracting_order: cur_frm.doc.name,
				rm_items: rm_items
			},
			callback: (r) => {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route('Form', doclist[0].doctype, doclist[0].name);
			}
		});
	}
}

extend_cscript(cur_frm.cscript, new erpnext.buying.SubcontractingOrderController({ frm: cur_frm }));

cur_frm.fields_dict['fg_items'].grid.get_field('bom').get_query = (doc, cdt, cdn) => {
	var d = locals[cdt][cdn];
	return {
		filters: [
			['BOM', 'item', '=', d.item_code],
			['BOM', 'is_active', '=', '1'],
			['BOM', 'docstatus', '=', '1'],
			['BOM', 'company', '=', doc.company]
		]
	};
}

let set_schedule_date = (frm) => {
	if (frm.doc.schedule_date) {
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, 'fg_items', 'schedule_date');
	}
}

let calculate_amount = (frm, cdt, cdn) => {
	let item = frappe.get_doc(cdt, cdn);
	if (item.item_code)
		item.amount = item.rate * item.qty;
	else
		item.rate = item.amount = 0.0;
	frm.refresh_fields();
}