// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/controllers/stock_controller.js");
frappe.require("assets/erpnext/js/utils.js");
frappe.provide("erpnext.stock");

frappe.ui.form.on("Stock Reconciliation", "get_items", function(frm) {
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
					}
					frm.refresh_field("items");
				}
			});
		}
	, __("Get Items"), __("Update"));
});

erpnext.stock.StockReconciliation = erpnext.stock.StockController.extend({
	onload: function() {
		this.set_default_expense_account();
	},

	set_default_expense_account: function() {
		var me = this;

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
						'group_or_ledger': 'Ledger'
					}
				}
			}
			this.frm.fields_dict["cost_center"].get_query = function() {
				return {
					"filters": {
						'company': me.frm.doc.company,
						'group_or_ledger': 'Ledger'
					}
				}
			}
		}
	},

	refresh: function() {
		if(this.frm.doc.docstatus==1) {
			this.show_stock_ledger();
			this.show_general_ledger();
		}
	},

});

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});

cur_frm.cscript.company = function(doc, cdt, cdn) {
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}

cur_frm.cscript.posting_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}
