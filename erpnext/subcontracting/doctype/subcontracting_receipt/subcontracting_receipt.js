// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('erpnext.buying');

erpnext.landed_cost_taxes_and_charges.setup_triggers('Subcontracting Receipt');

frappe.ui.form.on('Subcontracting Receipt', {
	setup: (frm) => {
		frm.ignore_doctypes_on_cancel_all = ['Serial and Batch Bundle'];
		frm.get_field('supplied_items').grid.cannot_add_rows = true;
		frm.get_field('supplied_items').grid.only_sortable();
		frm.trigger('set_queries');
	},

	refresh: (frm) => {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Stock Ledger'), () => {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
						company: frm.doc.company,
						show_cancelled_entries: frm.doc.docstatus === 2
					}
					frappe.set_route('query-report', 'Stock Ledger');
				}, __('View'));

			frm.add_custom_button(__('Accounting Ledger'), () => {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
						company: frm.doc.company,
						group_by: 'Group by Voucher (Consolidated)',
						show_cancelled_entries: frm.doc.docstatus === 2
					}
					frappe.set_route('query-report', 'General Ledger');
				}, __('View'));
		}

		if (!frm.doc.is_return && frm.doc.docstatus === 1 && frm.doc.per_returned < 100) {
			frm.add_custom_button(__('Subcontract Return'), () => {
					frappe.model.open_mapped_doc({
						method: 'erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_subcontract_return',
						frm: frm
					});
				}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Subcontracting Order'), () => {
					if (!frm.doc.supplier) {
						frappe.throw({
							title: __('Mandatory'),
							message: __('Please Select a Supplier')
						});
					}

					erpnext.utils.map_current_doc({
						method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt',
						source_doctype: 'Subcontracting Order',
						target: frm,
						setters: {
							supplier: frm.doc.supplier,
						},
						get_query_filters: {
							docstatus: 1,
							per_received: ['<', 100],
							company: frm.doc.company
						}
					});
				}, __('Get Items From'));

			frm.fields_dict.supplied_items.grid.update_docfield_property('consumed_qty', 'read_only', frm.doc.__onload && frm.doc.__onload.backflush_based_on === 'BOM');
		}

		frm.trigger('setup_quality_inspection');
		frm.trigger('set_route_options_for_new_doc');
	},

	set_warehouse: (frm) => {
		set_warehouse_in_children(frm.doc.items, 'warehouse', frm.doc.set_warehouse);
	},

	rejected_warehouse: (frm) => {
		set_warehouse_in_children(frm.doc.items, 'rejected_warehouse', frm.doc.rejected_warehouse);
	},

	get_scrap_items: (frm) => {
		frappe.call({
			doc: frm.doc,
			method: 'get_scrap_items',
			args: {
				recalculate_rate: true
			},
			freeze: true,
			freeze_message: __('Getting Scrap Items'),
			callback: (r) => {
				if (!r.exc) {
					frm.refresh();
				}
			}
		});
	},

	set_queries: (frm) => {
		frm.set_query('set_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			}
		});

		frm.set_query('rejected_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			}
		});

		frm.set_query('supplier_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			}
		});

		frm.set_query('warehouse', 'items', () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0
			}
		}));

		frm.set_query('rejected_warehouse', 'items', () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0
			}
		}));

		frm.set_query('expense_account', 'items', () => {
			return {
				query: 'erpnext.controllers.queries.get_expense_account',
				filters: { 'company': frm.doc.company }
			}
		});

		frm.set_query('batch_no', 'items', (doc, cdt, cdn) => {
			var row = locals[cdt][cdn];
			return {
				filters: {
					item: row.item_code
				}
			}
		});

		frm.set_query('serial_and_batch_bundle', 'items', (doc, cdt, cdn) => {
			return frm.events.get_serial_and_batch_bundle_filters(doc, cdt, cdn);
		});

		frm.set_query('rejected_serial_and_batch_bundle', 'items', (doc, cdt, cdn) => {
			return frm.events.get_serial_and_batch_bundle_filters(doc, cdt, cdn);
		});

		frm.set_query('batch_no', 'supplied_items', (doc, cdt, cdn) => {
			var row = locals[cdt][cdn];
			return {
				filters: {
					item: row.rm_item_code
				}
			}
		});

		frm.set_query('serial_and_batch_bundle', 'supplied_items', (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					'item_code': row.rm_item_code,
					'voucher_type': doc.doctype,
					'voucher_no': ['in', [doc.name, '']],
					'is_cancelled': 0,
				}
			}
		});
	},

	get_serial_and_batch_bundle_filters: (doc, cdt, cdn) => {
		let row = locals[cdt][cdn];
		return {
			filters: {
				'item_code': row.item_code,
				'voucher_type': doc.doctype,
				'voucher_no': ['in', [doc.name, '']],
				'is_cancelled': 0,
			}
		}
	},

	setup_quality_inspection: (frm) => {
		if (!frm.is_new() && frm.doc.docstatus === 0 && !frm.doc.is_return) {
			let transaction_controller = new erpnext.TransactionController({ frm: frm });
			transaction_controller.setup_quality_inspection();
		}
	},

	set_route_options_for_new_doc: (frm) => {
		let batch_no_field = frm.get_docfield('items', 'batch_no');
		if (batch_no_field) {
			batch_no_field.get_route_options_for_new_doc = (row) => {
				return {
					'item': row.doc.item_code
				}
			}
		}

		let item_sbb_field = frm.get_docfield('items', 'serial_and_batch_bundle');
		if (item_sbb_field) {
			item_sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					'item_code': row.doc.item_code,
					'voucher_type': frm.doc.doctype,
				}
			}
		}

		let rejected_item_sbb_field = frm.get_docfield('items', 'rejected_serial_and_batch_bundle');
		if (rejected_item_sbb_field) {
			rejected_item_sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					'item_code': row.doc.item_code,
					'voucher_type': frm.doc.doctype,
				}
			}
		}

		let rm_sbb_field = frm.get_docfield('supplied_items', 'serial_and_batch_bundle');
		if (rm_sbb_field) {
			rm_sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					'item_code': row.doc.rm_item_code,
					'voucher_type': frm.doc.doctype,
				}
			}
		}
	},
});

frappe.ui.form.on('Landed Cost Taxes and Charges', {
	amount: (frm, cdt, cdn) => {
		set_missing_values(frm);
		frm.events.set_base_amount(frm, cdt, cdn);
	},

	expense_account: (frm, cdt, cdn) => {
		frm.events.set_account_currency(frm, cdt, cdn);
	},

	additional_costs_remove: (frm) => {
		set_missing_values(frm);
	}
});

frappe.ui.form.on('Subcontracting Receipt Item', {
	item_code(frm) {
		set_missing_values(frm);
	},

	qty(frm) {
		set_missing_values(frm);
	},

	rate(frm) {
		set_missing_values(frm);
	},

	items_remove: (frm) => {
		set_missing_values(frm);
	},
});

frappe.ui.form.on('Subcontracting Receipt Supplied Item', {
	consumed_qty(frm) {
		set_missing_values(frm);
	},
});

let set_warehouse_in_children = (child_table, warehouse_field, warehouse) => {
	let transaction_controller = new erpnext.TransactionController();
	transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
}

let set_missing_values = (frm) => {
	frappe.call({
		doc: frm.doc,
		method: 'set_missing_values',
		callback: (r) => {
			if (!r.exc) frm.refresh();
		},
	});
}
