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
	erpnext.hide_naming_series();
	if(!doc.__islocal && !cint(doc.email_sent) && !doc.__unsaved
			&& inList(wn.boot.profile.can_write, doc.doctype)) {
		cur_frm.add_custom_button('Send', function() {
			return $c_obj(make_doclist(doc.doctype, doc.name), 'send_emails', '', function(r) {
				cur_frm.refresh();
			});
		})
	}

	if(doc.__islocal && !doc.send_from) {
		cur_frm.set_value("send_from", 
			repl("%(fullname)s <%(email)s>", wn.user_info(doc.owner)));
	}
	
	return wn.call({
		method: "support.doctype.newsletter.newsletter.get_lead_options",
		type: "GET",
		callback: function(r) {
			set_field_options("lead_source", r.message.sources.join("\n"))
			set_field_options("lead_status", r.message.statuses.join("\n"))
		}
	})
}