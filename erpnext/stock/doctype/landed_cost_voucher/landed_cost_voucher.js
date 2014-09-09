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
						['Account', 'account_type', 'in', ['Tax', 'Chargeable', 'Expense Account']],
						['Account', 'company', '=', me.frm.doc.company]
					]
				}
		};
		
		this.frm.add_fetch("purchase_receipt", "supplier", "supplier");
		this.frm.add_fetch("purchase_receipt", "posting_date", "posting_date");
		this.frm.add_fetch("purchase_receipt", "grand_total", "grand_total");
		
	}, 
	
	refresh: function() {
		var help_content = ['<table class="table table-bordered" style="background-color: #f9f9f9;">',
			'<tr><td>',
				'<h4><i class="icon-hand-right"></i> ',
					__('Notes'),
				':</h4>',
				'<ul>',
					'<li>',
						__("Charges will be distributed proportionately based on item amount"),
					'</li>',
					'<li>',
						__("Remove item if charges is not applicable to that item"),
					'</li>',
					'<li>',
						__("Charges are updated in Purchase Receipt against each item"),
					'</li>',
					'<li>',
						__("Item valuation rate is recalculated considering landed cost voucher amount"),
					'</li>',
					'<li>',
						__("Stock Ledger Entries and GL Entries are reposted for the selected Purchase Receipts"),
					'</li>',
				'</ul>',
			'</td></tr>',
		'</table>'].join("\n");

		set_field_options("landed_cost_help", help_content);
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
		this.set_applicable_charges_for_item();
	},
	
	set_total_taxes_and_charges: function() {
		total_taxes_and_charges = 0.0;
		$.each(this.frm.doc.landed_cost_taxes_and_charges, function(i, d) {
			total_taxes_and_charges += flt(d.amount)
		});
		cur_frm.set_value("total_taxes_and_charges", total_taxes_and_charges);
	},
	
	set_applicable_charges_for_item: function() {
		var me = this;
		if(this.frm.doc.landed_cost_taxes_and_charges.length) {
			var total_item_cost = 0.0;
			$.each(this.frm.doc.landed_cost_items, function(i, d) {
				total_item_cost += flt(d.amount)
			});
			
			$.each(this.frm.doc.landed_cost_items, function(i, item) {
				item.applicable_charges = flt(item.amount) *  flt(me.frm.doc.total_taxes_and_charges) / flt(total_item_cost)
			});
			refresh_field("landed_cost_items");
		}
	}
	
});

cur_frm.script_manager.make(erpnext.stock.LandedCostVoucher);