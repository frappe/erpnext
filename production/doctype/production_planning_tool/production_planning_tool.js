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


cur_frm.cscript.download_raw_material = function(doc, cdt, cdn) {
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
  return 'SELECT DISTINCT `tabBOM`.`name` FROM `tabBOM` WHERE `tabBOM`.`item` = "' + d.item_code + '" AND `tabBOM`.`is_active` = "Yes" AND `tabBOM`.docstatus = 1 AND `tabBOM`.`name` like "%s" ORDER BY `tabBOM`.`name` LIMIT 50';
}
