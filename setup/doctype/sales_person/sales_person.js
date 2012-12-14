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
	cur_frm.cscript.set_root_readonly(doc);
}

cur_frm.cscript.set_root_readonly = function(doc) {
	// read-only for root
	if(!doc.parent_sales_person) {
		cur_frm.perm = [[1,0,0], [1,0,0]];
		cur_frm.set_intro("This is a root sales person and cannot be edited.");
	} else {
		cur_frm.set_intro(null);
	}
}


cur_frm.cscript.onload = function(){

}

//get query select sales person
cur_frm.fields_dict['parent_sales_person'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabSales Person`.`name`,`tabSales Person`.`parent_sales_person` FROM `tabSales Person` WHERE `tabSales Person`.`is_group` = "Yes" AND `tabSales Person`.`docstatus`!= 2 AND `tabSales Person`.`name` !="'+doc.sales_person_name+'" AND `tabSales Person`.%(key)s LIKE "%s" ORDER BY  `tabSales Person`.`name` ASC LIMIT 50';
}

cur_frm.fields_dict['target_details'].grid.get_field("item_group").get_query = function(doc, cdt, cdn) {
  return 'SELECT `tabItem Group`.name FROM `tabItem Group` WHERE `tabItem Group`.is_group="No" AND `tabItem Group`.docstatus != 2 AND `tabItem Group`.%(key)s LIKE "%s" LIMIT 50'
}

cur_frm.fields_dict.employee.get_query = erpnext.utils.employee_query;