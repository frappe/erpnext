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

cur_frm.cscript.set_breadcrumbs = function(barea) {
	cur_frm.frm_head.appframe.add_breadcrumb(cur_frm.docname);
	cur_frm.frm_head.appframe.add_breadcrumb(' in <a href="#!Sales Browser/Item Group">\
		Item Group Tree</a>');
	cur_frm.frm_head.appframe.add_breadcrumb(' in <a href="#!selling-home">Selling</a>');
}

//get query select item group
cur_frm.fields_dict['parent_item_group'].get_query = function(doc,cdt,cdn) {
  return 'SELECT `tabItem Group`.`name`,`tabItem Group`.`parent_item_group` FROM `tabItem Group` WHERE `tabItem Group`.`is_group` = "Yes" AND  `tabItem Group`.`docstatus`!= 2 AND `tabItem Group`.`name` !="'+doc.item_group_name+'" AND `tabItem Group`.%(key)s LIKE "%s" ORDER BY  `tabItem Group`.`name` ASC LIMIT 50';
}