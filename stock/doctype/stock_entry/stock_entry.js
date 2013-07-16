// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

wn.require("public/app/js/controllers/stock_controller.js");
wn.provide("erpnext.stock");

erpnext.stock.StockEntry = erpnext.stock.StockController.extend({
	onload: function() {
		this.set_default_account();
	}, 
	
	set_default_account: function() {
		var me = this;
		
		if (sys_defaults.auto_inventory_accounting && !this.frm.doc.expense_adjustment_account) {
			if (this.frm.doc.purpose == "Sales Return") 
				account_for = "stock_in_hand_account";
			else if (this.frm.doc.purpose == "Purchase Return") 
				account_for = "stock_received_but_not_billed";
			else account_for = "stock_adjustment_account";
			
			this.frm.call({
				method: "accounts.utils.get_company_default",
				args: {
					"fieldname": account_for, 
					"company": this.frm.doc.company
				},
				callback: function(r) {
					if (!r.exc) me.frm.set_value("expense_adjustment_account", r.message);
				}
			});
		}
	},
	
	setup: function() {
		var me = this;
		
		this.frm.fields_dict.delivery_note_no.get_query = function() {
			return { query: "stock.doctype.stock_entry.stock_entry.query_sales_return_doc" };
		};
		
		this.frm.fields_dict.sales_invoice_no.get_query = 
			this.frm.fields_dict.delivery_note_no.get_query;
		
		this.frm.fields_dict.purchase_receipt_no.get_query = function() {
			return { 
				filters:{ 'docstatus': 1 }
			};
		};
		
		this.frm.fields_dict.mtn_details.grid.get_field('item_code').get_query = function() {
			if(in_list(["Sales Return", "Purchase Return"], me.frm.doc.purpose) && 
				me.get_doctype_docname()) {
					return {
						query: "stock.doctype.stock_entry.stock_entry.query_return_item",
						filters: {
							purpose: me.frm.doc.purpose,
							delivery_note_no: me.frm.doc.delivery_note_no,
							sales_invoice_no: me.frm.doc.sales_invoice_no,
							purchase_receipt_no: me.frm.doc.purchase_receipt_no
						}
					};
			} else {
				return erpnext.queries.item({is_stock_item: "Yes"});
			}
		};
		
		if (sys_defaults.auto_inventory_accounting) {
			this.frm.add_fetch("company", "stock_adjustment_account", "expense_adjustment_account");

			this.frm.fields_dict["expense_adjustment_account"].get_query = function() {
				return {
					filters: { 
						"company": me.frm.doc.company,
						"group_or_ledger": "Ledger"
					}
				}
			}
		}
	},
	
	onload_post_render: function() {
		if(this.frm.doc.__islocal && (this.frm.doc.production_order || this.frm.doc.bom_no) 
			&& !getchildren('Stock Entry Detail', this.frm.doc.name, 'mtn_details').length) {
				// if production order / bom is mentioned, get items
				this.get_items();
		}
	},
	
	refresh: function() {
		var me = this;
		erpnext.hide_naming_series();
		this.toggle_related_fields(this.frm.doc);
		this.toggle_enable_bom();
		if (this.frm.doc.docstatus==1) {
			this.show_stock_ledger();
			if(wn.boot.auto_inventory_accounting)
				this.show_general_ledger();
		}
		
		if(this.frm.doc.docstatus === 1 && 
				wn.boot.profile.can_create.indexOf("Journal Voucher")!==-1) {
			if(this.frm.doc.purpose === "Sales Return") {
				this.frm.add_custom_button("Make Credit Note", function() { me.make_return_jv(); });
				this.add_excise_button();
			} else if(this.frm.doc.purpose === "Purchase Return") {
				this.frm.add_custom_button("Make Debit Note", function() { me.make_return_jv(); });
				this.add_excise_button();
			}
		}
		
	},
	
	on_submit: function() {
		this.clean_up();
	},
	
	after_cancel: function() {
		this.clean_up();
	},
	
	clean_up: function() {
		// Clear Production Order record from locals, because it is updated via Stock Entry
		if(this.frm.doc.production_order && 
				this.frm.doc.purpose == "Manufacture/Repack") {
			wn.model.remove_from_locals("Production Order", 
				this.frm.doc.production_order);
		}
	},
	
	get_items: function() {
		this.frm.call({
			doc: this.frm.doc,
			method: "get_items",
			callback: function(r) {
				if(!r.exc) refresh_field("mtn_details");
			}
		});
	},
	
	qty: function(doc, cdt, cdn) {
		var d = locals[cdt][cdn];
		d.transfer_qty = flt(d.qty) * flt(d.conversion_factor);
		refresh_field('mtn_details');
	},
	
	production_order: function() {
		this.toggle_enable_bom();
		
		this.frm.call({
			method: "get_production_order_details",
			args: {production_order: this.frm.doc.production_order}
		});
	},
	
	toggle_enable_bom: function() {
		this.frm.toggle_enable("bom_no", !this.frm.doc.production_order);
	},
	
	get_doctype_docname: function() {
		if(this.frm.doc.purpose === "Sales Return") {
			if(this.frm.doc.delivery_note_no && this.frm.doc.sales_invoice_no) {
				// both specified
				msgprint(wn._("You can not enter both Delivery Note No and Sales Invoice No. \
					Please enter any one."));
				
			} else if(!(this.frm.doc.delivery_note_no || this.frm.doc.sales_invoice_no)) {
				// none specified
				msgprint(wn._("Please enter Delivery Note No or Sales Invoice No to proceed"));
				
			} else if(this.frm.doc.delivery_note_no) {
				return {doctype: "Delivery Note", docname: this.frm.doc.delivery_note_no};
				
			} else if(this.frm.doc.sales_invoice_no) {
				return {doctype: "Sales Invoice", docname: this.frm.doc.sales_invoice_no};
				
			}
		} else if(this.frm.doc.purpose === "Purchase Return") {
			if(this.frm.doc.purchase_receipt_no) {
				return {doctype: "Purchase Receipt", docname: this.frm.doc.purchase_receipt_no};
				
			} else {
				// not specified
				msgprint(wn._("Please enter Purchase Receipt No to proceed"));
				
			}
		}
	},
	
	add_excise_button: function() {
		if(wn.boot.control_panel.country === "India")
			this.frm.add_custom_button("Make Excise Invoice", function() {
				var excise = wn.model.make_new_doc_and_get_name('Journal Voucher');
				excise = locals['Journal Voucher'][excise];
				excise.voucher_type = 'Excise Voucher';
				loaddoc('Journal Voucher', excise.name);
			});
	},
	
	make_return_jv: function() {
		if(this.get_doctype_docname()) {
			this.frm.call({
				method: "make_return_jv",
				args: {
					stock_entry: this.frm.doc.name
				},
				callback: function(r) {
					if(!r.exc) {
						var jv_name = wn.model.make_new_doc_and_get_name('Journal Voucher');
						var jv = locals["Journal Voucher"][jv_name];
						$.extend(jv, r.message[0]);
						$.each(r.message.slice(1), function(i, jvd) {
							var child = wn.model.add_child(jv, "Journal Voucher Detail", "entries");
							$.extend(child, jvd);
						});
						loaddoc("Journal Voucher", jv_name);
					}

				}
			});
		}
	},

});

cur_frm.cscript = new erpnext.stock.StockEntry({frm: cur_frm});

cur_frm.cscript.toggle_related_fields = function(doc) {
	disable_from_warehouse = inList(["Material Receipt", "Sales Return"], doc.purpose);
	disable_to_warehouse = inList(["Material Issue", "Purchase Return"], doc.purpose)
	
	cur_frm.toggle_enable("from_warehouse", !disable_from_warehouse);
	cur_frm.toggle_enable("to_warehouse", !disable_to_warehouse);
		
	cur_frm.fields_dict["mtn_details"].grid.set_column_disp("s_warehouse", !disable_from_warehouse);
	cur_frm.fields_dict["mtn_details"].grid.set_column_disp("t_warehouse", !disable_to_warehouse);
		
	if(doc.purpose == 'Purchase Return') {
		doc.customer = doc.customer_name = doc.customer_address = 
			doc.delivery_note_no = doc.sales_invoice_no = null;
		doc.bom_no = doc.production_order = doc.fg_completed_qty = null;
	} else if(doc.purpose == 'Sales Return') {
		doc.supplier=doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no=null;
		doc.bom_no = doc.production_order = doc.fg_completed_qty = null;
	} else {
		doc.customer = doc.customer_name = doc.customer_address = 
			doc.delivery_note_no = doc.sales_invoice_no = doc.supplier = 
			doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no = null;
	}
}

cur_frm.cscript.delivery_note_no = function(doc,cdt,cdn){
	if(doc.delivery_note_no) get_server_fields('get_cust_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.sales_invoice_no = function(doc,cdt,cdn){
	if(doc.sales_invoice_no) get_server_fields('get_cust_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.customer = function(doc,cdt,cdn){
	if(doc.customer) get_server_fields('get_cust_addr','','',doc,cdt,cdn,1);
}

cur_frm.cscript.purchase_receipt_no = function(doc,cdt,cdn){
	if(doc.purchase_receipt_no)	get_server_fields('get_supp_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.supplier = function(doc,cdt,cdn){
	if(doc.supplier) get_server_fields('get_supp_addr','','',doc,cdt,cdn,1);

}

cur_frm.fields_dict['production_order'].get_query = function(doc) {
	return{
		filters:[
			['Production Order', 'docstatus', '=', 1],
			['Production Order', 'qty', '>','`tabProduction Order`.produced_qty']
		]
	}
}

cur_frm.cscript.purpose = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc, cdt, cdn);
}

// copy over source and target warehouses
cur_frm.fields_dict['mtn_details'].grid.onrowadd = function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	if(!d.s_warehouse && doc.from_warehouse) {
		d.s_warehouse = doc.from_warehouse
		refresh_field('s_warehouse', cdn, 'mtn_details')
	}
	if(!d.t_warehouse && doc.to_warehouse) {
		d.t_warehouse = doc.to_warehouse
		refresh_field('t_warehouse', cdn, 'mtn_details')
	}
}

// Overloaded query for link batch_no
cur_frm.fields_dict['mtn_details'].grid.get_field('batch_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];		
	if(d.item_code) {
		return{
			query: "stock.doctype.stock_entry.stock_entry.get_batch_no",
			filters:{
				'item_code': d.item_code,
				's_warehouse': d.s_warehouse,
				'posting_date': doc.posting_date
			}
		}			
	} else {
		msgprint("Please enter Item Code to get batch no");
	}
}

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	args = {
		'item_code'		: d.item_code,
		'warehouse'		: cstr(d.s_warehouse) || cstr(d.t_warehouse),
		'transfer_qty'	: d.transfer_qty,
		'serial_no'		: d.serial_no,
		'bom_no'		: d.bom_no
	};
	get_server_fields('get_item_details',JSON.stringify(args),'mtn_details',doc,cdt,cdn,1);
}

cur_frm.cscript.s_warehouse = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	args = {
		'item_code'		: d.item_code,
		'warehouse'		: cstr(d.s_warehouse) || cstr(d.t_warehouse),
		'transfer_qty'	: d.transfer_qty,
		'serial_no'		: d.serial_no,
		'bom_no'		: d.bom_no,
		'qty'			: d.s_warehouse ? -1* d.qty : d.qty
	}
	get_server_fields('get_warehouse_details', JSON.stringify(args), 
		'mtn_details', doc, cdt, cdn, 1);
}

cur_frm.cscript.t_warehouse = cur_frm.cscript.s_warehouse;

cur_frm.cscript.uom = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if(d.uom && d.item_code){
		var arg = {'item_code':d.item_code, 'uom':d.uom, 'qty':d.qty}
		get_server_fields('get_uom_details',JSON.stringify(arg),'mtn_details', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.validate = function(doc, cdt, cdn) {
	cur_frm.cscript.validate_items(doc);
	if($.inArray(cur_frm.doc.purpose, ["Purchase Return", "Sales Return"])!==-1)
		validated = cur_frm.cscript.get_doctype_docname() ? true : false;
}

cur_frm.cscript.validate_items = function(doc) {
	cl =	getchildren('Stock Entry Detail',doc.name,'mtn_details');
	if (!cl.length) {
		alert("Item table can not be blank");
		validated = false;
	}
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{ query:"controllers.queries.customer_query" } }

cur_frm.fields_dict.supplier.get_query = function(doc,cdt,cdn) {
	return{	query:"controllers.queries.supplier_query" } }
