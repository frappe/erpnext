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

cur_frm.cscript.refresh = function(doc) {
	cur_frm.toggle_display('warehouse_name', doc.__islocal);
}

cur_frm.cscript.merge = function(doc, cdt, cdn) {
	if (!doc.merge_with) {
		msgprint("Please enter the warehouse to which you want to merge?");
		return;
	}
	var check = confirm("Are you sure you want to merge this warehouse into " 
		+ doc.merge_with + "?");
	if (check) {
		return $c_obj(make_doclist(cdt, cdn), 'merge_warehouses', '', '');
	}
}