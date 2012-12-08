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

// Settings
cur_frm.cscript.onload_post_render = function(doc, cdt, cdn){
	cur_frm.call({
		doc: cur_frm.doc,
		method: 'get_transactions',
		callback: function(r) {
			cur_frm.cscript.update_selects(r);
			cur_frm.cscript.select_doc_for_series(doc, cdt, cdn);
		}
	})
}

cur_frm.cscript.update_selects = function(r) {
	set_field_options('select_doc_for_series', r.message.transactions);
	set_field_options('prefix', r.message.prefixes);
}


cur_frm.cscript.select_doc_for_series = function(doc, cdt, cdn) {
	cur_frm.toggle_display(['help_html','set_options', 'user_must_always_select', 'update'], 
		doc.select_doc_for_series)

	var callback = function(r, rt){
		locals[cdt][cdn].set_options = r.message;
		refresh_field('set_options');
		if(r.message && r.message.split('\n')[0]=='') {
			cur_frm.set_value('user_must_always_select', 1)
		}
	}

	if(doc.select_doc_for_series)
		$c_obj(make_doclist(doc.doctype, doc.name),'get_options','',callback)
}

cur_frm.cscript.update = function() {
	cur_frm.call_server('update_series', '', cur_frm.cscript.update_selects)
}

cur_frm.cscript.prefix = function(doc, dt, dn) {
	cur_frm.call_server('get_current', '', function(r) {
		refresh_field('current_value');
	})
}
