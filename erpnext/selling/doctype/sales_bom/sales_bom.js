// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	cur_frm.toggle_enable('new_item_code', doc.__islocal);
}

cur_frm.fields_dict.new_item_code.get_query = function() {
	return{
		query: "erpnext.selling.doctype.sales_bom.sales_bom.get_new_item_code"
	}
}
cur_frm.fields_dict.new_item_code.query_description = __('Please select Item where "Is Stock Item" is "No" and "Is Sales Item" is "Yes" and there is no other Sales BOM');

cur_frm.cscript.item_code = function(doc, dt, dn) {
	var d = locals[dt][dn];
	if (d.item_code){
		return get_server_fields('get_item_details', d.item_code, 'sales_bom_items', doc ,dt, dn, 1);
	}
}
