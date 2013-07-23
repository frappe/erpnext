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
wn.provide("erpnext");

$.extend(erpnext, {
	get_currency: function(company) {
		if(!company && cur_frm)
			company = cur_frm.doc.company;
		if(company)
			return wn.model.get_doc(":Company", company).default_currency || wn.boot.sysdefaults.currency;
		else
			return wn.boot.sysdefaults.currency;
	},
	
	hide_naming_series: function() {
		if(cur_frm.fields_dict.naming_series) {
			cur_frm.toggle_display("naming_series", cur_frm.doc.__islocal?true:false);
		}
	},
	
	hide_company: function() {
		if(cur_frm.fields_dict.company) {
			var companies = Object.keys(locals[":Company"]);
			if(companies.length === 1) {
				if(!cur_frm.doc.company) cur_frm.set_value("company", companies[0]);
				cur_frm.toggle_display("company", false);
			}
		}
	},
	
	add_for_territory: function() {
		if(cur_frm.doc.__islocal && 
			wn.model.get_doclist(cur_frm.doc.doctype, cur_frm.doc.name).length === 1) {
				var territory = wn.model.add_child(cur_frm.doc, "For Territory", 
					"valid_for_territories");
				territory.territory = wn.defaults.get_default("territory");
		}
	},
});