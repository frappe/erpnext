// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc) {
	return wn.call({
		method: "support.doctype.newsletter.newsletter.get_lead_options",
		type: "GET",
		callback: function(r) {
			set_field_options("lead_source", r.message.sources.join("\n"))
			set_field_options("lead_status", r.message.statuses.join("\n"))
		}
	});
}

cur_frm.cscript.refresh = function(doc) {
	erpnext.hide_naming_series();
	if(!doc.__islocal && !cint(doc.email_sent) && !doc.__unsaved
			&& inList(wn.boot.profile.can_write, doc.doctype)) {
		cur_frm.add_custom_button(wn._('Send'), function() {
			return $c_obj(make_doclist(doc.doctype, doc.name), 'send_emails', '', function(r) {
				cur_frm.refresh();
			});
		})
	}
	
	cur_frm.cscript.setup_dashboard();

	if(doc.__islocal && !doc.send_from) {
		cur_frm.set_value("send_from", 
			repl("%(fullname)s <%(email)s>", wn.user_info(doc.owner)));
	}
}

cur_frm.cscript.setup_dashboard = function() {
	cur_frm.dashboard.reset();
	if(!cur_frm.doc.__islocal && cint(cur_frm.doc.email_sent) && cur_frm.doc.__status_count) {
		var stat = cur_frm.doc.__status_count;
		var total = wn.utils.sum($.map(stat, function(v) { return v; }));
		if(total) {
			$.each(stat, function(k, v) {
				stat[k] = flt(v * 100 / total, 2);
			});
			
			cur_frm.dashboard.add_progress("Status", [
				{
					title: stat["Sent"] + "% Sent",
					width: stat["Sent"],
					progress_class: "progress-bar-success"
				},
				{
					title: stat["Sending"] + "% Sending",
					width: stat["Sending"],
					progress_class: "progress-bar-warning"
				},
				{
					title: stat["Error"] + "% Error",
					width: stat["Error"],
					progress_class: "progress-bar-danger"
				}
			]);
		}
	}
}