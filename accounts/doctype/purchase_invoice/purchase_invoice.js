// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tname = "Purchase Invoice Item";
cur_frm.cscript.fname = "entries";
cur_frm.cscript.other_fname = "purchase_tax_details";

wn.provide("erpnext.accounts");
wn.require('app/accounts/doctype/purchase_taxes_and_charges_master/purchase_taxes_and_charges_master.js');
wn.require('app/buying/doctype/purchase_common/purchase_common.js');

erpnext.accounts.PurchaseInvoice = erpnext.buying.BuyingController.extend({
	onload: function() {
		this._super();
		
		if(!this.frm.doc.__islocal) {
			// show credit_to in print format
			if(!this.frm.doc.supplier && this.frm.doc.credit_to) {
				this.frm.set_df_property("credit_to", "print_hide", 0);
			}
		}
	},
	
	refresh: function(doc) {
		this._super();
		
		// Show / Hide button
		if(doc.docstatus==1 && doc.outstanding_amount > 0)
			this.frm.add_custom_button('Make Payment Entry', this.make_bank_voucher);

		if(doc.docstatus==1) { 
			cur_frm.add_custom_button('View Ledger', function() {
				wn.route_options = {
					"voucher_no": doc.name,
					"from_date": doc.posting_date,
					"to_date": doc.posting_date,
				};
				wn.set_route("general-ledger");
			});
		}

		if(doc.docstatus===0) {
			cur_frm.add_custom_button(wn._('From Purchase Order'), 
				function() {
					wn.model.map_current_doc({
						method: "buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
						source_doctype: "Purchase Order",
						get_query_filters: {
							supplier: cur_frm.doc.supplier || undefined,
							docstatus: 1,
							status: ["!=", "Stopped"],
							per_billed: ["<", 99.99],
							company: cur_frm.doc.company
						}
					})
				});

			cur_frm.add_custom_button(wn._('From Purchase Receipt'), 
				function() {
					wn.model.map_current_doc({
						method: "stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
						source_doctype: "Purchase Receipt",
						get_query_filters: {
							supplier: cur_frm.doc.supplier || undefined,
							docstatus: 1,
							company: cur_frm.doc.company
						}
					})
				});	
			
		}

		this.is_opening(doc);
	},
	
	credit_to: function() {
		this.supplier();
	},
	
	write_off_amount: function() {
		this.calculate_outstanding_amount();
		this.frm.refresh_fields();
	},
	
	allocated_amount: function() {
		this.calculate_total_advance("Purchase Invoice", "advance_allocation_details");
		this.frm.refresh_fields();
	}, 

	tc_name: function() {
		this.get_terms();
	},
	
	entries_add: function(doc, cdt, cdn) {
		var row = wn.model.get_doc(cdt, cdn);
		this.frm.script_manager.copy_from_first_row("entries", row, ["expense_head", "cost_center"]);
	}
});

cur_frm.script_manager.make(erpnext.accounts.PurchaseInvoice);

cur_frm.cscript.is_opening = function(doc, dt, dn) {
	hide_field('aging_date');
	if (doc.is_opening == 'Yes') unhide_field('aging_date');
}

cur_frm.cscript.make_bank_voucher = function() {
	return wn.call({
		method: "accounts.doctype.journal_voucher.journal_voucher.get_payment_entry_from_purchase_invoice",
		args: {
			"purchase_invoice": cur_frm.doc.name,
		},
		callback: function(r) {
			var doclist = wn.model.sync(r.message);
			wn.set_route("Form", doclist[0].doctype, doclist[0].name);
		}
	});
}


cur_frm.fields_dict['supplier_address'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'supplier':  doc.supplier}
	}
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return{
		filters:{'supplier':  doc.supplier}
	}	
}

cur_frm.fields_dict['entries'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
	return {
		query:"controllers.queries.item_query",
		filters:{
			'is_purchase_item': 'Yes'	
		}
	}	 
}

cur_frm.fields_dict['credit_to'].get_query = function(doc) {
	return{
		filters:{
			'debit_or_credit': 'Credit',
			'is_pl_account': 'No',
			'group_or_ledger': 'Ledger',
			'company': doc.company
		}
	}	
}

// Get Print Heading
cur_frm.fields_dict['select_print_heading'].get_query = function(doc, cdt, cdn) {
return{
		filters:[
			['Print Heading', 'docstatus', '!=', 2]
		]
	}	
}

cur_frm.set_query("expense_head", "entries", function(doc) {
	return{
		query: "accounts.doctype.purchase_invoice.purchase_invoice.get_expense_account",
		filters: {'company': doc.company}
	}
});

cur_frm.cscript.expense_head = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.expense_head){
		var cl = getchildren('Purchase Invoice Item', doc.name, 'entries', doc.doctype);
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].expense_head) cl[i].expense_head = d.expense_head;
		}
	}
	refresh_field('entries');
}

cur_frm.fields_dict["entries"].grid.get_field("cost_center").get_query = function(doc) {
	return {
		filters: { 
			'company': doc.company,
			'group_or_ledger': 'Ledger'
		}

	}
}

cur_frm.cscript.cost_center = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(d.idx == 1 && d.cost_center){
		var cl = getchildren('Purchase Invoice Item', doc.name, 'entries', doc.doctype);
		for(var i = 0; i < cl.length; i++){
			if(!cl[i].cost_center) cl[i].cost_center = d.cost_center;
		}
	}
	refresh_field('entries');
}

cur_frm.fields_dict['entries'].grid.get_field('project_name').get_query = function(doc, cdt, cdn) {
	return{
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}	
}


cur_frm.cscript.select_print_heading = function(doc,cdt,cdn){
	if(doc.select_print_heading){
		// print heading
		cur_frm.pformat.print_heading = doc.select_print_heading;
	}
	else
		cur_frm.pformat.print_heading = "Purchase Invoice";
}