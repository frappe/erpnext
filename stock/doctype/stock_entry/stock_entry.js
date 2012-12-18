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

cur_frm.cscript.refresh = function(doc) { 
	erpnext.hide_naming_series();
	cur_frm.cscript.toggle_related_fields(doc);
}



cur_frm.cscript.toggle_related_fields = function(doc) {
	
	
	
	
	
	
	
	if(doc.purpose.startswith("Production Order") || doc.purpose == "Other") {
		
		
		
		
	}
	

	if (doc.purpose == 'Production Order' || doc.purpose == 'Other') {
		unhide_field('get_items');
		hide_field(['from_warehouse', 'to_warehouse','purchase_receipt_no', 
			'delivery_note_no', 'sales_invoice_no','warehouse_html']);
		if (doc.purpose=='Production Order') unhide_field(['production_order', 'process']);
		else {
			doc.production_order = doc.process = '';
			hide_field(['production_order', 'process']);
		}

		doc.from_warehouse = '';
		doc.to_warehouse = '';
		refresh_field(['from_warehosue', 'to_warehouse']);
		if (doc.process == 'Backflush' || doc.purpose == 'Other') {
			unhide_field('fg_completed_qty');
		}
		else{
			hide_field('fg_completed_qty');
			doc.fg_completed_qty = 0;
		}
	} else {
		unhide_field(['from_warehouse', 'to_warehouse']);
		hide_field(['production_order', 'process', 'get_items',	'fg_completed_qty', 
			'purchase_receipt_no','delivery_note_no', 'sales_invoice_no']);
		doc.production_order = '';
		doc.process = '';
		doc.fg_completed_qty = 0;
	}
	
 
	if(doc.purpose == 'Purchase Return') {
		doc.customer = doc.customer_name = doc.customer_address = 
			doc.delivery_note_no = doc.sales_invoice_no = '';
		unhide_field(['supplier','supplier_name','supplier_address','purchase_receipt_no']);
		$(cur_frm.fields_dict.contact_section.row.wrapper).toggle(true);
	}
	else if(doc.purpose == 'Sales Return'){
		doc.supplier=doc.supplier_name = doc.supplier_address=doc.purchase_receipt_no='';
		unhide_field(['customer', 'customer_name', 'customer_address', 
			'delivery_note_no', 'sales_invoice_no']);
		$(cur_frm.fields_dict.contact_section.row.wrapper).toggle(true);
	} else{
		doc.customer = doc.customer_name = doc.customer_address = 
			doc.delivery_note_no = doc.sales_invoice_no = doc.supplier = 
			doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no = '';
	}
	refresh_many(lst);
}

cur_frm.cscript.delivery_note_no = function(doc,cdt,cdn){
	if(doc.delivery_note_no) get_server_fields('get_cust_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.sales_invoice_no = function(doc,cdt,cdn){
	if(doc.sales_invoice_no) get_server_fields('get_cust_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.customer = function(doc,cdt,cdn){
	if(doc.customer)	get_server_fields('get_cust_addr','','',doc,cdt,cdn,1);
}

cur_frm.cscript.purchase_receipt_no = function(doc,cdt,cdn){
	if(doc.purchase_receipt_no)	get_server_fields('get_supp_values','','',doc,cdt,cdn,1);
}

cur_frm.cscript.supplier = function(doc,cdt,cdn){
	if(doc.supplier)	get_server_fields('get_supp_addr','','',doc,cdt,cdn,1);

}

cur_frm.fields_dict['production_order'].get_query = function(doc) {
	 return 'SELECT DISTINCT `tabProduction Order`.`name` FROM `tabProduction Order` WHERE `tabProduction Order`.`docstatus` = 1 AND `tabProduction Order`.`qty` > ifnull(`tabProduction Order`.`produced_qty`,0) AND `tabProduction Order`.`name` like "%s" ORDER BY `tabProduction Order`.`name` DESC LIMIT 50';
}

cur_frm.cscript.purpose = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc, cdt, cdn);
}

cur_frm.cscript.process = function(doc, cdt, cdn) {
	cur_frm.cscript.toggle_related_fields(doc, cdt, cdn);
}

// item code - only if quantity present in source warehosue
//
var fld = cur_frm.fields_dict['mtn_details'].grid.get_field('item_code');
fld.query_description = "If Source Warehouse is selected, only items present in the warehouse with actual qty > 0 will be selected"
fld.get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
		
	if(d.s_warehouse) {
		return 'SELECT tabItem.name, tabItem.description, tabBin.actual_qty '
		+'FROM tabItem, tabBin '
		+'WHERE tabItem.name = tabBin.item_code '
		+'AND ifnull(`tabBin`.`actual_qty`,0) > 0 '
		+'AND tabBin.warehouse="'+ d.s_warehouse +'" '
		+'AND tabItem.docstatus < 2 '
		+'AND (ifnull(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` > NOW() OR `tabItem`.`end_of_life`="0000-00-00") '
		+'AND tabItem.%(key)s LIKE "%s" '
		+'ORDER BY tabItem.name ASC '
		+'LIMIT 50'
	} else {
		return 'SELECT tabItem.name, tabItem.description '
		+'FROM tabItem '
		+'WHERE tabItem.docstatus < 2 '
		+'AND (ifnull(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life` > NOW() OR `tabItem`.`end_of_life`="0000-00-00") '
		+'AND tabItem.%(key)s LIKE "%s" '
		+'ORDER BY tabItem.name ASC '
		+'LIMIT 50'
	}
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
		'fg_item'		: d.fg_item,
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
		'fg_item'		: d.fg_item,
		'bom_no'		: d.bom_no
	}
	get_server_fields('get_warehouse_details', JSON.stringify(args), 
		'mtn_details', doc, cdt, cdn, 1);
}

cur_frm.cscript.t_warehouse = cur_frm.cscript.s_warehouse;

cur_frm.cscript.transfer_qty = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (doc.from_warehouse && (flt(d.transfer_qty) > flt(d.actual_qty))) {
		alert("Transfer Quantity is more than Available Qty");
	}
}

cur_frm.cscript.qty = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	set_multiple('Stock Entry Detail', d.name, {'transfer_qty': flt(d.qty) * flt(d.conversion_factor)}, 'mtn_details');
	refresh_field('mtn_details');
}

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