// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


wn.provide("erpnext.stock");
wn.require("public/app/js/controllers/stock_controller.js");

erpnext.stock.LandedCostWizard = erpnext.stock.StockController.extend({		
	setup: function() {
		var me = this;
		this.frm.fields_dict.lc_pr_details.grid.get_field('purchase_receipt').get_query = 
			function() {
				if(!me.frm.doc.company) msgprint(wn._("Please enter company first"));
				return {
					filters:[
						['Purchase Receipt', 'docstatus', '=', '1'],
						['Purchase Receipt', 'company', '=', me.frm.doc.company],
					]
				}
		};
	
		this.frm.fields_dict.landed_cost_details.grid.get_field('account_head').get_query = 				function() {
				if(!me.frm.doc.company) msgprint(wn._("Please enter company first"));
				return {
					filters:[
						['Account', 'group_or_ledger', '=', 'Ledger'],
						['Account', 'account_type', 'in', 'Tax, Chargeable'],
						['Account', 'is_pl_account', '=', 'Yes'],
						['Account', 'debit_or_credit', '=', 'Debit'],
						['Account', 'company', '=', me.frm.doc.company]
					]
				}
		}, 
	
		this.frm.fields_dict.landed_cost_details.grid.get_field('cost_center').get_query =
			function() {
				if(!me.frm.doc.company) msgprint(wn._("Please enter company first"));
				return {
					filters:[
						['Cost Center', 'group_or_ledger', '=', 'Ledger'],
						['Cost Center', 'company', '=', me.frm.doc.company]						
					]
				}
		}
	}
});

cur_frm.script_manager.make(erpnext.stock.LandedCostWizard);