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

		frm.set_query("expense_account", "items", function () {
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: { 'company': frm.doc.company }
			};
		});
	},

	refresh: (frm) => {
		if (frm.doc.docstatus > 0) {
			frm.add_custom_button(__("Stock Ledger"), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));

			frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					company: frm.doc.company,
					group_by: "Group by Voucher (Consolidated)",
					show_cancelled_entries: frm.doc.docstatus === 2
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
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
						title: __("Mandatory"),
						message: __("Please Select a Supplier")
					});
				}

				erpnext.utils.map_current_doc({
					method: 'erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt',
					source_doctype: "Subcontracting Order",
					target: frm,
					setters: {
						supplier: frm.doc.supplier,
					},
					get_query_filters: {
						docstatus: 1,
						per_received: ["<", 100],
						company: frm.doc.company
					}
				});
			}, __("Get Items From"));
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