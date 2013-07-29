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

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(!doc.status) set_multiple(cdt, cdn, {status:'In Store'});
	if(doc.__islocal) hide_field(['supplier_name','address_display'])
}


cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	flds = ['status', 'item_code', 'warehouse', 'purchase_document_type', 
	'purchase_document_no', 'purchase_date', 'purchase_time', 'purchase_rate', 
	'supplier']
	for(i=0;i<flds.length;i++) {
		cur_frm.set_df_property(flds[i], 'read_only', doc.__islocal ? 0 : 1);
	}
}

// item details
// -------------
cur_frm.add_fetch('item_code', 'item_name', 'item_name')
cur_frm.add_fetch('item_code', 'item_group', 'item_group')
cur_frm.add_fetch('item_code', 'brand', 'brand')
cur_frm.add_fetch('item_code', 'description', 'description')
cur_frm.add_fetch('item_code', 'warranty_period', 'warranty_period')

// customer
// ---------
cur_frm.add_fetch('customer', 'customer_name', 'customer_name')
cur_frm.add_fetch('customer', 'address', 'delivery_address')
cur_frm.add_fetch('customer', 'territory', 'territory')

// territory
// ----------
cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return{
		filters:{'is_group': "No"}
	}
}

// Supplier
//-------------
cur_frm.cscript.supplier = function(doc,dt,dn) {
	if(doc.supplier) return get_server_fields('get_default_supplier_address', JSON.stringify({supplier: doc.supplier}),'', doc, dt, dn, 1);
	if(doc.supplier) unhide_field(['supplier_name','address_display']);
}

//item code
//----------
cur_frm.fields_dict['item_code'].get_query = function(doc,cdt,cdn) {
 	return{
		query:"controllers.queries.item_query",
		filters:{
			'has_serial_no': 'Yes'	
		}
	}	
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query:"controllers.queries.customer_query"
	}
}

cur_frm.fields_dict.supplier.get_query = function(doc,cdt,cdn) {
	return{
		query:"controllers.queries.supplier_query"
	}
}