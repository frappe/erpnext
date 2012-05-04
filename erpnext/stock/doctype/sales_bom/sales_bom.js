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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

 

cur_frm.cscript.onload = function(doc, cdt, cdn) {
    
  if(!doc.price_list) set_multiple(cdt,cdn,{price_list:sys_defaults.price_list_name});
}

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	if(!doc.__islocal) {
		hide_field('new_item_code');
	}
}

/* Get Item Code */
cur_frm.cscript.item_code = function(doc, dt, dn) {
  var d = locals[dt][dn];
  if (d.item_code){
    get_server_fields('get_item_details', d.item_code, 'sales_bom_items', doc ,dt, dn, 1);
  }
}

cur_frm.cscript.price_list = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt,cdn), 'get_rates', '', function(r,rt){refresh_field('sales_bom_items');});
}

cur_frm.cscript.currency = function(doc, cdt, cdn) {
  $c_obj(make_doclist(cdt,cdn), 'get_rates', '', function(r,rt){refresh_field('sales_bom_items');});
}

cur_frm.cscript.find_sales_bom = function(doc, dt, dn) {
  $c_obj(make_doclist(dt,dn), 'check_duplicate', 1, '');
}