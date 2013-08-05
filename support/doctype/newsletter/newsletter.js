// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

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