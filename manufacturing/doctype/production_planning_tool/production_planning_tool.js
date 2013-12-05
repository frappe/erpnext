// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	cur_frm.set_value("company", wn.defaults.get_default("company"))
	cur_frm.set_value("use_multi_level_bom", 1)
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.disable_save();
}

cur_frm.cscript.sales_order = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.sales_order) {
		return get_server_fields('get_so_details', d.sales_order, 'pp_so_details', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.item_code = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return get_server_fields('get_item_details', d.item_code, 'pp_details', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.download_materials_required = function(doc, cdt, cdn) {
	return $c_obj(make_doclist(cdt, cdn), 'validate_data', '', function(r, rt) {
		if (!r['exc'])
			$c_obj_csv(make_doclist(cdt, cdn), 'download_raw_materials', '', '');
	});
}

cur_frm.fields_dict['pp_details'].grid.get_field('item_code').get_query = function(doc) {
 	return erpnext.queries.item({
		'ifnull(tabItem.is_pro_applicable, "No")': 'Yes'
	});
}

cur_frm.fields_dict['pp_details'].grid.get_field('bom_no').get_query = function(doc) {
	var d = locals[this.doctype][this.docname];
	if (d.item_code) {
		return {
			query:"controllers.queries.bom",
			filters:{'item': cstr(d.item_code)}
		}
	} else msgprint(wn._("Please enter Item first"));
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query:"controllers.queries.customer_query"
	}
}

cur_frm.fields_dict.pp_so_details.grid.get_field("customer").get_query =
	cur_frm.fields_dict.customer.get_query;