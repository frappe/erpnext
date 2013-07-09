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

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.toggle_enable('new_item_code', doc.__islocal);
	if(!doc.__islocal) {
		cur_frm.add_custom_button("Check for Duplicates", function() {
			cur_frm.call_server('check_duplicate', 1)			
		}, 'icon-search')
	}
}

cur_frm.fields_dict.new_item_code.get_query = function() {
	return 'select name, description from tabItem where is_stock_item="No" and is_sales_item="Yes"\
		and name not in (select name from `tabSales BOM`)\
		and `%(key)s` like "%s"'
}
cur_frm.fields_dict.new_item_code.query_description = 'Select Item where "Is Stock Item" is "No" \
	and "Is Sales Item" is "Yes" and there is no other Sales BOM';

cur_frm.cscript.item_code = function(doc, dt, dn) {
	var d = locals[dt][dn];
	if (d.item_code){
		get_server_fields('get_item_details', d.item_code, 'sales_bom_items', doc ,dt, dn, 1);
	}
}