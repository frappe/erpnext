// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	cur_frm.set_value("company", frappe.defaults.get_user_default("company"))
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
	return $c_obj(doc, 'validate_data', '', function(r, rt) {
		if (!r['exc'])
			$c_obj_csv(doc, 'download_raw_materials', '', '');
	});
}


cur_frm.fields_dict['pp_so_details'].grid.get_field('sales_order').get_query = function(doc) {
	var args = { "docstatus": 1 };
	if(doc.customer) {
		args["customer"] = doc.customer;
	}

 	return { filters: args }
}

cur_frm.fields_dict['pp_details'].grid.get_field('item_code').get_query = function(doc) {
 	return erpnext.queries.item({
		'is_pro_applicable': 'Yes'
	});
}

cur_frm.fields_dict['pp_details'].grid.get_field('bom_no').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return {
			query: "erpnext.controllers.queries.bom",
			filters:{'item': cstr(d.item_code)}
		}
	} else msgprint(__("Please enter Item first"));
}

cur_frm.fields_dict.customer.get_query = function(doc,cdt,cdn) {
	return{
		query: "erpnext.controllers.queries.customer_query"
	}
}

cur_frm.fields_dict.pp_so_details.grid.get_field("customer").get_query =
	cur_frm.fields_dict.customer.get_query;
