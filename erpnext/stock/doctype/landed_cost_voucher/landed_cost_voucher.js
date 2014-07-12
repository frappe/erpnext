// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


frappe.provide("erpnext.stock");
frappe.require("assets/erpnext/js/controllers/stock_controller.js");

erpnext.stock.LandedCostVoucher = erpnext.stock.StockController.extend({		
	setup: function() {
		var me = this;
		this.frm.fields_dict.landed_cost_purchase_receipts.grid.get_field('purchase_receipt').get_query = 
			function() {
				if(!me.frm.doc.company) msgprint(__("Please enter company first"));
				return {
					filters:[
						['Purchase Receipt', 'docstatus', '=', '1'],
						['Purchase Receipt', 'company', '=', me.frm.doc.company],
					]
				}
		};
	
		this.frm.fields_dict.landed_cost_taxes_and_charges.grid.get_field('account').get_query = function() {
				if(!me.frm.doc.company) msgprint(__("Please enter company first"));
				return {
					filters:[
						['Account', 'group_or_ledger', '=', 'Ledger'],
						['Account', 'account_type', 'in', ['Tax', 'Chargeable']],
						['Account', 'company', '=', me.frm.doc.company]
					]
				}
		};
		
		this.frm.add_fetch("purchase_receipt", "supplier", "supplier");
		this.frm.add_fetch("purchase_receipt", "posting_date", "posting_date");
		this.frm.add_fetch("purchase_receipt", "grand_total", "grand_total");
		
	}, 
	
	get_items_from_purchase_receipts: function() {
		var me = this;
		if(!this.frm.doc.landed_cost_purchase_receipts.length) {
			msgprint(__("Please enter Purchase Receipt first"));
		} else {
			return this.frm.call({
				doc: me.frm.doc,
				method: "get_items_from_purchase_receipts"
			});
		}
	}, 
	
	amount: function() {
		this.set_total_taxes_and_charges();
		this.set_new_valuation_rate();
	},
	
	set_total_taxes_and_charges: function() {
		total_taxes_and_charges = 0.0;
		$.each(this.frm.doc.landed_cost_taxes_and_charges, function(i, d) {
			total_taxes_and_charges += flt(d.amount)
		});
		cur_frm.set_value("total_taxes_and_charges", total_taxes_and_charges);
	},
	
	set_new_valuation_rate: function() {
		var me = this;
		if(this.frm.doc.landed_cost_taxes_and_charges.length) {
			var total_item_cost = 0.0;
			$.each(this.frm.doc.landed_cost_items, function(i, d) {
				total_item_cost += flt(d.amount)
			});
			
			$.each(this.frm.doc.landed_cost_items, function(i, item) {
				var charges_for_item = flt(item.amount) *  flt(me.frm.doc.total_taxes_and_charges) / flt(total_item_cost)
				item.new_valuation_rate = flt(item.old_valuation_rate) + charges_for_item
			});
			refresh_field("landed_cost_items");
		}
	}
	
});

cur_frm.script_manager.make(erpnext.stock.LandedCostVoucher);