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
	doc.company = sys_defaults.company;
	refresh_field("company");
}

cur_frm.cscript.refresh = function(doc) {
	cur_frm.disable_save();
}

cur_frm.cscript.sales_order = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.sales_order) {
		get_server_fields('get_so_details', d.sales_order, 'pp_so_details', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.item_code = function(doc,cdt,cdn) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		get_server_fields('get_item_details', d.item_code, 'pp_details', doc, cdt, cdn, 1);
	}
}

cur_frm.cscript.download_materials_required = function(doc, cdt, cdn) {
	$c_obj(make_doclist(cdt, cdn), 'validate_data', '', function(r, rt) {
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
		return erpnext.queries.bom({item: cstr(d.item_code)});
	} else msgprint(" Please enter Item first");
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;

cur_frm.fields_dict.pp_so_details.grid.get_field("customer").get_query =
	erpnext.utils.customer_query;