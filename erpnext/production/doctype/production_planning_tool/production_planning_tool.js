cur_frm.cscript.item_code = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		get_server_fields('get_item_details', d.item_code, 'pp_details', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.sales_order = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.sales_order) {
		get_server_fields('get_so_details', d.sales_order, 'pp_so_details', doc, cdt, cdn, 1);
	}
}


cur_frm.cscript['Download Raw Material'] = function(doc, cdt, cdn) {
	var callback = function(r, rt){
		if (r.message) 
			$c_obj_csv(make_doclist(cdt, cdn), 'download_raw_materials', '', '');
	}
	$c_obj(make_doclist(cdt, cdn), 'validate_data', '', callback)
}

//-------------------------------------------------------------------------------
//

cur_frm.fields_dict['pp_details'].grid.get_field('item_code').get_query = function(doc) {
  return 'SELECT DISTINCT `tabItem`.`name`,`tabItem`.`item_name` FROM `tabItem` WHERE (IFNULL(`tabItem`.`end_of_life`,"") = "" OR `tabItem`.`end_of_life`="0000-00-00" OR `tabItem`.`end_of_life` > NOW()) AND `tabItem`.is_pro_applicable = "Yes" AND tabItem.%(key)s like "%s" ORDER BY `tabItem`.`name` LIMIT 50';
}

cur_frm.fields_dict['pp_details'].grid.get_field('bom_no').get_query = function(doc) {
  var d = locals[this.doctype][this.docname];
  return 'SELECT DISTINCT `tabBill Of Materials`.`name` FROM `tabBill Of Materials` WHERE `tabBill Of Materials`.`item` = "' + d.item_code + '" AND `tabBill Of Materials`.`is_active` = "Yes" AND `tabBill Of Materials`.docstatus = 1 AND `tabBill Of Materials`.`name` like "%s" ORDER BY `tabBill Of Materials`.`name` LIMIT 50';
}
