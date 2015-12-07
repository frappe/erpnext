// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/controllers/stock_controller.js");
frappe.require("assets/erpnext/js/utils.js");
frappe.provide("erpnext.stock");

frappe.ui.form.on("Stock Reconciliation", {
	onload: function(frm) {
		// end of life
		frm.set_query("item_code", "items", function(doc, cdt, cdn) {
			return {
				filters:[
					['Item', 'end_of_life', '>=', frappe.datetime.nowdate()]
				]
			}
		});
	},

	refresh: function(frm) {
		if(frm.doc.docstatus < 1) {
			frm.add_custom_button(__("Get Items"), function() {
				frm.events.get_items(frm);
			});
		}
	},

	company: function(frm) {
		erpnext.get_fiscal_year(frm.doc.company, frm.doc.posting_date);
	},

	posting_date: function(frm) {
		erpnext.get_fiscal_year(frm.doc.company, frm.doc.posting_date);
	},

	get_items: function(frm) {
		frappe.prompt({label:"Warehouse", fieldtype:"Link", options:"Warehouse", reqd: 1},
			function(data) {
				frappe.call({
					method:"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_items",
					args: {
						warehouse: data.warehouse,
						posting_date: frm.doc.posting_date,
						posting_time: frm.doc.posting_time
					},
					callback: function(r) {
						var items = [];
						frm.clear_table("items");
						for(var i=0; i< r.message.length; i++) {
							var d = frm.add_child("items");
							$.extend(d, r.message[i]);
							if(!d.qty) d.qty = null;
							if(!d.valuation_rate) d.valuation_rate = null;
						}
						frm.refresh_field("items");
					}
				});
			}
		, __("Get Items"), __("Update"));
	},

	set_valuation_rate_and_qty: function(frm, cdt, cdn) {
		var d = frappe.model.get_doc(cdt, cdn);
		if(d.item_code && d.warehouse) {
			frappe.call({
				method: "erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_stock_balance_for",
				args: {
					item_code: d.item_code,
					warehouse: d.warehouse,
					posting_date: frm.doc.posting_date,
					posting_time: frm.doc.posting_time
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, "qty", r.message.qty);
					frappe.model.set_value(cdt, cdn, "valuation_rate", r.message.rate);
					frappe.model.set_value(cdt, cdn, "current_qty", r.message.qty);
					frappe.model.set_value(cdt, cdn, "current_valuation_rate", r.message.rate);
				}
			});
		}
	}
});

frappe.ui.form.on("Stock Reconciliation Item", {
	warehouse: function(frm, cdt, cdn) {
		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	},
	item_code: function(frm, cdt, cdn) {
		frm.events.set_valuation_rate_and_qty(frm, cdt, cdn);
	}
});

erpnext.stock.StockReconciliation = erpnext.stock.StockController.extend({
	onload: function() {
		this.set_default_expense_account();
	},

	set_default_expense_account: function() {
		var me = this;
		if(this.frm.doc.company) {
			if (sys_defaults.auto_accounting_for_stock && !this.frm.doc.expense_account) {
				return this.frm.call({
					method: "erpnext.accounts.utils.get_company_default",
					args: {
						"fieldname": "stock_adjustment_account",
						"company": this.frm.doc.company
					},
					callback: function(r) {
						if (!r.exc) {
							me.frm.set_value("expense_account", r.message);
						}
					}
				});
			}
		}
	},

	setup: function() {
		var me = this;
		this.frm.get_docfield("items").allow_bulk_edit = 1;

		if (sys_defaults.auto_accounting_for_stock) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_account");
			this.frm.add_fetch("company", "cost_center", "cost_center");

			this.frm.fields_dict["expense_account"].get_query = function() {
				return {
					"filters": {
						'company': me.frm.doc.company,
						"is_group": 0
					}
				}
			}
			this.frm.fields_dict["cost_center"].get_query = function() {
				return {
					"filters": {
						'company': me.frm.doc.company,
						"is_group": 0
					}
				}
			}
		}
	},

	refresh: function() {
		if(this.frm.doc.docstatus==1) {
			this.show_stock_ledger();
			if (cint(frappe.defaults.get_default("auto_accounting_for_stock"))) {
				this.show_general_ledger();
			}
		}
	},

});

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});
