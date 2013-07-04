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

$.extend(cur_frm.cscript, {
	refresh: function() {
		cur_frm.cscript.set_exchange_rate_label();
	},
	
	from_currency: function() {
		cur_frm.cscript.set_exchange_rate_label();
	},
	
	to_currency: function() {
		cur_frm.cscript.set_exchange_rate_label();
	},
	
	set_exchange_rate_label: function() {
		if(cur_frm.doc.from_currency && cur_frm.doc.to_currency) {
			var default_label = wn._(wn.meta.docfield_map[cur_frm.doctype]["exchange_rate"].label);
			console.log(default_label + 
				repl(" (1 %(from_currency)s = [?] %(to_currency)s)", cur_frm.doc));
			cur_frm.fields_dict.exchange_rate.set_label(default_label + 
				repl(" (1 %(from_currency)s = [?] %(to_currency)s)", cur_frm.doc));
		}
	}
});