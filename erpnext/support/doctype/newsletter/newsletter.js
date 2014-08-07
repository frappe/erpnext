// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.onload = function(doc) {
	return frappe.call({
		method: "erpnext.support.doctype.newsletter.newsletter.get_lead_options",
		type: "GET",
		callback: function(r) {
			set_field_options("lead_source", r.message.sources.join("\n"))
			set_field_options("lead_status", r.message.statuses.join("\n"))
		}
	});
}

cur_frm.cscript.refresh = function(doc) {
	erpnext.toggle_naming_series();
	if(!doc.__islocal && !cint(doc.email_sent) && !doc.__unsaved
			&& inList(frappe.boot.user.can_write, doc.doctype)) {
		cur_frm.add_custom_button(__('Send'), function() {
			return $c_obj(doc, 'send_emails', '', function(r) {
				cur_frm.refresh();
			});
		}, "icon-play", "btn-success");
	}

	cur_frm.cscript.setup_dashboard();

	if(doc.__islocal && !doc.send_from) {
		cur_frm.set_value("send_from",
			repl("%(fullname)s <%(email)s>", frappe.user_info(doc.owner)));
	}
}

cur_frm.cscript.setup_dashboard = function() {
	cur_frm.dashboard.reset();
	if(!cur_frm.doc.__islocal && cint(cur_frm.doc.email_sent) && cur_frm.doc.__onload && cur_frm.doc.__onload.status_count) {
		var stat = cur_frm.doc.__onload.status_count;
		var total = frappe.utils.sum($.map(stat, function(v) { return v; }));
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
