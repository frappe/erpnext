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
	onload_post_render: function() {
		if(this.frm.doc.__islocal && (this.frm.doc.production_order || this.frm.doc.bom_no) 
			&& !getchildren('Stock Entry Detail', this.frm.doc.name, 'mtn_details').length) {
				// if production order / bom is mentioned, get items
				this.get_items();
		}
	},
	
	refresh: function() {
		erpnext.hide_naming_series();
		this.toggle_related_fields(this.frm.doc);
		this.toggle_enable_bom();
		if (this.frm.doc.docstatus==1) {
			this.show_stock_ledger();
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
	return 'select name from `tabProduction Order` \
		where docstatus = 1 and qty > ifnull(produced_qty,0) AND %(key)s like "%s%%" \
		order by name desc limit 50';
}

cur_frm.cscript.purpose = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc, cdt, cdn);
}

// item code - only if quantity present in source warehosue
var fld = cur_frm.fields_dict['mtn_details'].grid.get_field('item_code');
fld.query_description = "If Source Warehouse is selected, items with existing stock \
	for that warehouse will be selected";

fld.get_query = function() {
	return erpnext.queries.item({is_stock_item: "Yes"});
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
		if (d.s_warehouse) {
			return "select batch_no from `tabStock Ledger Entry` sle \
				where item_code = '" + d.item_code + "' and warehouse = '" + d.s_warehouse +
				"' and ifnull(is_cancelled, 'No') = 'No' and batch_no like '%s' \
				and exists(select * from `tabBatch` where \
				name = sle.batch_no and expiry_date >= '" + doc.posting_date + 
				"' and docstatus != 2) group by batch_no having sum(actual_qty) > 0 \
				order by batch_no desc limit 50";
		} else {
			return "SELECT name FROM tabBatch WHERE docstatus != 2 AND item = '" + 
				d.item_code + "' and expiry_date >= '" + doc.posting_date + 
				"' AND name like '%s' ORDER BY name DESC LIMIT 50";
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
}

cur_frm.cscript.validate_items = function(doc) {
	cl =	getchildren('Stock Entry Detail',doc.name,'mtn_details');
	if (!cl.length) {
		alert("Item table can not be blank");
		validated = false;
	}
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;

cur_frm.fields_dict.supplier.get_query = erpnext.utils.supplier_query;