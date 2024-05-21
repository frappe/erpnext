// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide('erpnext.buying');

{% include 'erpnext/stock/landed_taxes_and_charges_common.js' %};

frappe.ui.form.on('Subcontracting Receipt', {
	setup: (frm) => {
		frm.get_field('supplied_items').grid.cannot_add_rows = true;
		frm.get_field('supplied_items').grid.only_sortable();

		frm.set_query('set_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query('rejected_warehouse', () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			};
		});

		frm.set_query('supplier_warehouse', () => {
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

		frm.set_query('rejected_warehouse', 'items', () => ({
			filters: {
				company: frm.doc.company,
				is_group: 0
			}
		}));

		frm.set_query('expense_account', 'items', function () {
			return {
				query: 'erpnext.controllers.queries.get_expense_account',
				filters: { 'company': frm.doc.company }
			};
		});

		frm.set_query('batch_no', 'items', function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					item: row.item_code
				}
			}
		});

		frm.set_query('batch_no', 'supplied_items', function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					item: row.rm_item_code
				}
			}
		});
	},

	refresh: (frm) => {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__('Stock Ledger'), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route('query-report', 'Stock Ledger');
			}, __('View'));

			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					group_by: 'Group by Voucher (Consolidated)',
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route('query-report', 'General Ledger');
			}, __('View'));
		}

		if (!frm.doc.is_return && frm.doc.docstatus == 1 && frm.doc.per_returned < 100) {
			frm.add_custom_button(__('Subcontract Return'), function () {
				frappe.model.open_mapped_doc({
					method: 'erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_subcontract_return',
					frm: frm
				});
			}, __('Create'));
			frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(__('Subcontracting Order'), function () {
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

		let batch_no_field = frm.get_docfield('items', 'batch_no');
		if (batch_no_field) {
			batch_no_field.get_route_options_for_new_doc = function(row) {
				return {
					'item': row.doc.item_code
				}
			};
		}
	},

	set_warehouse: (frm) => {
		set_warehouse_in_children(frm.doc.items, 'warehouse', frm.doc.set_warehouse);
	},

	rejected_warehouse: (frm) => {
		set_warehouse_in_children(frm.doc.items, 'rejected_warehouse', frm.doc.rejected_warehouse);
	},
});

frappe.ui.form.on('Landed Cost Taxes and Charges', {
	amount: function (frm, cdt, cdn) {
		frm.events.set_base_amount(frm, cdt, cdn);
	},

	expense_account: function (frm, cdt, cdn) {
		frm.events.set_account_currency(frm, cdt, cdn);
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
<<<<<<< HEAD
=======

	items_delete: (frm) => {
		set_missing_values(frm);
	},

	add_serial_batch_bundle(frm, cdt, cdn) {
		let item = locals[cdt][cdn];

		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.type_of_transaction = item.qty > 0 ? "Inward" : "Outward";
				item.is_rejected = false;

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						let qty = Math.abs(r.total_qty);
						if (frm.doc.is_return) {
							qty = qty * -1;
						}

						let update_values = {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							qty: qty / flt(item.conversion_factor || 1, precision("conversion_factor", item)),
						};

						if (r.warehouse) {
							update_values["warehouse"] = r.warehouse;
						}

						frappe.model.set_value(item.doctype, item.name, update_values);
					}
				});
			}
		});
	},

	add_serial_batch_for_rejected_qty(frm, cdt, cdn) {
		let item = locals[cdt][cdn];

		frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"]).then((r) => {
			if (r.message && (r.message.has_batch_no || r.message.has_serial_no)) {
				item.has_serial_no = r.message.has_serial_no;
				item.has_batch_no = r.message.has_batch_no;
				item.type_of_transaction = item.rejected_qty > 0 ? "Inward" : "Outward";
				item.is_rejected = true;

				new erpnext.SerialBatchPackageSelector(frm, item, (r) => {
					if (r) {
						let qty = Math.abs(r.total_qty);
						if (frm.doc.is_return) {
							qty = qty * -1;
						}

						let update_values = {
							serial_and_batch_bundle: r.name,
							use_serial_batch_fields: 0,
							rejected_qty:
								qty / flt(item.conversion_factor || 1, precision("conversion_factor", item)),
						};

						if (r.warehouse) {
							update_values["rejected_warehouse"] = r.warehouse;
						}

						frappe.model.set_value(item.doctype, item.name, update_values);
					}
				});
			}
		});
	},
>>>>>>> 4261c3474b (fix: not able to delete line items in the subcontracting receipt (#41569))
});

frappe.ui.form.on('Subcontracting Receipt Supplied Item', {
	consumed_qty(frm) {
		set_missing_values(frm);
	},
});

let set_warehouse_in_children = (child_table, warehouse_field, warehouse) => {
	let transaction_controller = new erpnext.TransactionController();
	transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
};

let set_missing_values = (frm) => {
	frappe.call({
		doc: frm.doc,
		method: 'set_missing_values',
		callback: (r) => {
			if (!r.exc) frm.refresh();
		},
	});
};
