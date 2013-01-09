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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

cur_frm.cscript.refresh = function(doc, dt, dn) {
	cur_frm.toggle_enable('year_start_date', doc.__islocal)
	
	if (!doc.__islocal && (doc.name != sys_defaults.fiscal_year)) {
		cur_frm.add_custom_button("Set as Default", cur_frm.cscript.set_as_default);
		cur_frm.set_intro("To set this Fiscal Year as Deafult, click on 'Set as Default'");
	} else cur_frm.set_intro("");
}

cur_frm.cscript.set_as_default = function() {
	wn.call({
		doc: cur_frm.doc,
		method: "set_as_default"
	});
}