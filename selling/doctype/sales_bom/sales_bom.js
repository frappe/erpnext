// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.toggle_enable('new_item_code', doc.__islocal);
	if(!doc.__islocal) {
		cur_frm.add_custom_button(wn._("Check for Duplicates"), function() {
			return cur_frm.call_server('check_duplicate', 1)			
		}, 'icon-search')
	}
}

cur_frm.fields_dict.new_item_code.get_query = function() {
	return{
		query: "selling.doctype.sales_bom.sales_bom.get_new_item_code"
	}
}
cur_frm.fields_dict.new_item_code.query_description = wn._('Select Item where "Is Stock Item" is "No"')+ 
wn._('and "Is Sales Item" is "Yes" and there is no other Sales BOM');

cur_frm.cscript.item_code = function(doc, dt, dn) {
	var d = locals[dt][dn];
	if (d.item_code){
		return get_server_fields('get_item_details', d.item_code, 'sales_bom_items', doc ,dt, dn, 1);
	}
}