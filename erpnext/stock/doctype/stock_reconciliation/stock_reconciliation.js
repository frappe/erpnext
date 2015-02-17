// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.require("assets/erpnext/js/controllers/stock_controller.js");
frappe.require("assets/erpnext/js/utils.js");
frappe.provide("erpnext.stock");

frappe.ui.form.on("Stock Reconciliation", "get_items", function(frm) {
	frappe.prompt({label:"Warehouse", fieldtype:"Link", options:"Warehouse", reqd: 1},
		function(data) {
			frappe.call({
				method:"erpnext.stock.doctype.stock_reconciliation.stock_reconciliation.get_items",
				args: {warehouse: data.warehouse},
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
	);
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
		this.frm.get_field("items").grid.allow_build_edit();

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
		//
	},

	// show_download_template: function() {
	// 	var me = this;
	// 	this.frm.add_custom_button(__("Download Template"), function() {
	// 		this.title = __("Stock Reconcilation Template");
	// 		frappe.tools.downloadify([[__("Stock Reconciliation")],
	// 			["----"],
	// 			[__("Stock Reconciliation can be used to update the stock on a particular date, usually as per physical inventory.")],
	// 			[__("When submitted, the system creates difference entries to set the given stock and valuation on this date.")],
	// 			[__("It can also be used to create opening stock entries and to fix stock value.")],
	// 			["----"],
	// 			[__("Notes:")],
	// 			[__("Item Code and Warehouse should already exist.")],
	// 			[__("You can update either Quantity or Valuation Rate or both.")],
	// 			[__("If no change in either Quantity or Valuation Rate, leave the cell blank.")],
	// 			["----"],
	// 			["Item Code", "Warehouse", "Quantity", "Valuation Rate"]], null, this);
	// 		return false;
	// 	}, "icon-download");
	// },

});

cur_frm.cscript = new erpnext.stock.StockReconciliation({frm: cur_frm});

cur_frm.cscript.company = function(doc, cdt, cdn) {
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}

cur_frm.cscript.posting_date = function(doc, cdt, cdn){
	erpnext.get_fiscal_year(doc.company, doc.posting_date);
}
