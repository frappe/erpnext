// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.stock");
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Stock Reconciliation", {
	setup(frm) {
		frm.ignore_doctypes_on_cancel_all = ["Serial and Batch Bundle"];
	},

	onload: function (frm) {
		frm.add_fetch("item_code", "item_name", "item_name");

		// end of life
		frm.set_query("item_code", "items", function (doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {
					is_stock_item: 1,
				},
			};
		});
		frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
			var item = locals[cdt][cdn];
			return {
				filters: {
					item: item.item_code,
				},
			};
		});

		frm.set_query("serial_and_batch_bundle", "items", (doc, cdt, cdn) => {
			let row = locals[cdt][cdn];
			return {
				filters: {
					item_code: row.item_code,
					voucher_type: doc.doctype,
					voucher_no: ["in", [doc.name, ""]],
					is_cancelled: 0,
				},
			};
		});

		let sbb_field = frm.get_docfield("items", "serial_and_batch_bundle");
		if (sbb_field) {
			sbb_field.get_route_options_for_new_doc = (row) => {
				return {
					item_code: row.doc.item_code,
					warehouse: row.doc.warehouse,
					voucher_type: frm.doc.doctype,
				};
			};
		}

		if (frm.doc.company) {
			erpnext.queries.setup_queries(frm, "Warehouse", function () {
				return erpnext.queries.warehouse(frm.doc);
			});
		}

		if (!frm.doc.expense_account) {
			frm.trigger("set_expense_account");
		}

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	company: function (frm) {
		frm.trigger("toggle_display_account_head");
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	refresh: function (frm) {
		if (frm.doc.docstatus < 1) {
			frm.add_custom_button(__("Fetch Items from Warehouse"), function () {
				frm.events.get_items(frm);
			});
		}

		if (frm.doc.company) {
			frm.trigger("toggle_display_account_head");
		}

		frm.events.set_fields_onload_for_line_item(frm);
	},

	set_fields_onload_for_line_item(frm) {
		if (frm.is_new() && frm.doc?.items && cint(frappe.user_defaults?.use_serial_batch_fields) === 1) {
			frm.doc.items.forEach((item) => {
				if (!item.serial_and_batch_bundle) {
					frappe.model.set_value(item.doctype, item.name, "use_serial_batch_fields", 1);
				}
			});
		}
	},

	scan_barcode: function (frm) {
		const barcode_scanner = new erpnext.utils.BarcodeScanner({ frm: frm });
		barcode_scanner.process_scan();
	},

	scan_mode: function (frm) {
		if (frm.doc.scan_mode) {
			frappe.show_alert({
				message: __("Scan mode enabled, existing quantity will not be fetched."),
				indicator: "green",
			});
		}
	},

	set_warehouse: function (frm) {
		let transaction_controller = new erpnext.TransactionController({ frm: frm });
		transaction_controller.autofill_warehouse(frm.doc.items, "warehouse", frm.doc.set_warehouse);
	},

	get_items: function (frm) {
		let fields = [
			{
				label: "Warehouse",
				fieldname: "warehouse",
				fieldtype: "Link",
				options: "Warehouse",
				reqd: 1,
				get_query: function () {
					return {
						filters: {
							company: frm.doc.company,
						},
					};
				},
			},
			{
				label: "Item Code",
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
			},
			{
				label: __("Ignore Empty Stock"),
				fieldname: "ignore_empty_stock",
				fieldtype: "Check",
			},
		];

		frappe.prompt(
			fields,
			function (data) {
				frappe.call({
					method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_items",
					args: {
						warehouse: data.warehouse,
						posting_date: frm.doc.posting_date,
						posting_time: frm.doc.posting_time,
						company: frm.doc.company,
						item_code: data.item_code,
						ignore_empty_stock: data.ignore_empty_stock,
					},
					callback: function (r) {
						if (r.exc || !r.message || !r.message.length) return;

						frm.clear_table("items");

						r.message.forEach((row) => {
							let item = frm.add_child("items");
							$.extend(item, row);

							item.qty = item.qty || 0;
							item.valuation_rate = item.valuation_rate || 0;
							item.use_serial_batch_fields = cint(
								frappe.user_defaults?.use_serial_batch_fields
							);
						});
						frm.refresh_field("items");
					},
				});
			},
			__("Get Items"),
			__("Update")
		);
	},

	posting_date: function (frm) {
		frm.trigger("set_valuation_rate_and_qty_for_all_items");
	},

	posting_time: function (frm) {
		frm.trigger("set_valuation_rate_and_qty_for_all_items");
	},

	set_valuation_rate_and_qty_for_all_items: function (frm) {
		frm.doc.items.forEach((row) => {
			frm.events.set_valuation_rate_and_qty(frm, row.doctype, row.name);
		});
	},

	set_valuation_rate_and_qty: function (frm, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);

		if (d.item_code && d.warehouse) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for",
				args: {
					item_code: d.item_code,
					warehouse: d.warehouse,
					posting_date: frm.doc.posting_date,
					posting_time: frm.doc.posting_time,
					batch_no: d.batch_no,
					row: d,
					company: frm.doc.company,
				},
				callback: function (r) {
					const row = frappe.model.get_doc(cdt, cdn);
					if (!frm.doc.scan_mode) {
						frappe.model.set_value(cdt, cdn, "qty", r.message.qty);
					}
					frappe.model.set_value(cdt, cdn, "valuation_rate", r.message.rate);
					frappe.model.set_value(cdt, cdn, "current_qty", r.message.qty);
					frappe.model.set_value(cdt, cdn, "current_valuation_rate", r.message.rate);
					frappe.model.set_value(cdt, cdn, "current_amount", r.message.rate * r.message.qty);
					frappe.model.set_value(cdt, cdn, "amount", row.qty * row.valuation_rate);
					frappe.model.set_value(cdt, cdn, "current_serial_no", r.message.serial_nos);
					frappe.model.set_value(
						cdt,
						cdn,
						"use_serial_batch_fields",
						r.message.use_serial_batch_fields
					);

					if (frm.doc.purpose == "Stock Reconciliation" && !frm.doc.scan_mode) {
						frappe.model.set_value(cdt, cdn, "serial_no", r.message.serial_nos);
					}
				},
			});
		}
	},

	set_amount_quantity: function (doc, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if (d.qty && d.valuation_rate) {
			frappe.model.set_value(cdt, cdn, "amount", flt(d.qty) * flt(d.valuation_rate));
			frappe.model.set_value(cdt, cdn, "quantity_difference", flt(d.qty) - flt(d.current_qty));
			frappe.model.set_value(cdt, cdn, "amount_difference", flt(d.amount) - flt(d.current_amount));
		}
	},
	toggle_display_account_head: function (frm) {
		frm.toggle_display(
			["expense_account", "cost_center"],
			erpnext.is_perpetual_inventory_enabled(frm.doc.company)
		);
	},
	purpose: function (frm) {
		frm.trigger("set_expense_account");
	},
	set_expense_account: function (frm) {
		if (frm.doc.company && erpnext.is_perpetual_inventory_enabled(frm.doc.company)) {
			return frm.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_difference_account",
				args: {
					purpose: frm.doc.purpose,
					company: frm.doc.company,
				},
				callback: function (r) {
					if (!r.exc) {
						frm.set_value("expense_account", r.message);
					}
				},
			});
		}
	},
});

frappe.ui.form.on("Stock Reconciliation Item", {
	warehouse: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.batch_no && !frm.doc.scan_mode) {
			frappe.model.set_value(child.cdt, child.cdn, "batch_no", "");
		}

		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	item_code: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.batch_no && !frm.doc.scan_mode) {
			frappe.model.set_value(cdt, cdn, "batch_no", "");
		}

		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	batch_no: function (frm, cdt, cdn) {
		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},

	qty: function (frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);

		let row = locals[cdt][cdn];
		if (row.use_serial_batch_fields && !row.qty && row.serial_no) {
			frappe.model.set_value(cdt, cdn, "serial_no", "");
		}
	},

	valuation_rate: function (frm, cdt, cdn) {
		frm.events.set_amount_quantity(frm, cdt, cdn);
	},

	serial_no: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];

		if (child.serial_no) {
			const serial_nos = child.serial_no.trim().split("\n");
			frappe.model.set_value(cdt, cdn, "qty", serial_nos.length);
		}
	},

	items_add: function (frm, cdt, cdn) {
		var item = frappe.get_doc(cdt, cdn);
		if (!item.warehouse && frm.doc.set_warehouse) {
			frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.set_warehouse);
		}

		if (item.docstatus === 0 && cint(frappe.user_defaults?.use_serial_batch_fields) === 1) {
			frappe.model.set_value(item.doctype, item.name, "use_serial_batch_fields", 1);
		}
	},

	add_serial_batch_bundle(frm, cdt, cdn) {
		erpnext.utils.pick_serial_and_batch_bundle(frm, cdt, cdn, "Inward");
	},
});

erpnext.stock.StockReconciliation = class StockReconciliation extends erpnext.stock.StockController {
	setup() {
		var me = this;

		this.setup_posting_date_time_check();

		if (me.frm.doc.company && erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
			this.frm.add_fetch("company", "cost_center", "cost_center");
		}
		this.frm.fields_dict["expense_account"].get_query = function () {
			if (erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					filters: {
						company: me.frm.doc.company,
						is_group: 0,
					},
				};
			}
		};
		this.frm.fields_dict["cost_center"].get_query = function () {
			if (erpnext.is_perpetual_inventory_enabled(me.frm.doc.company)) {
				return {
					filters: {
						company: me.frm.doc.company,
						is_group: 0,
					},
				};
			}
		};
	}

	refresh() {
		if (this.frm.doc.docstatus > 0) {
			this.show_stock_ledger();
			erpnext.utils.view_serial_batch_nos(this.frm);
			if (erpnext.is_perpetual_inventory_enabled(this.frm.doc.company)) {
				this.show_general_ledger();
			}
		}
	}
};

cur_frm.cscript = new erpnext.stock.StockReconciliation({ frm: cur_frm });
