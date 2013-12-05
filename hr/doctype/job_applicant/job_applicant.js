// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// For license information, please see license.txt

cur_frm.cscript = {
	onload: function(doc, dt, dn) {
		if(in_list(user_roles,'System Manager')) {
			cur_frm.footer.help_area.innerHTML = '<p><a href="#Form/Jobs Email Settings">'+wn._("Jobs Email Settings")+'</a><br>\
				<span class="help">'+wn._('Automatically extract Job Applicants from a mail box ')+'e.g. "jobs@example.com"</span></p>';
		}
	},
	refresh: function(doc) {
		cur_frm.cscript.make_listing(doc);
	},
	make_listing: function(doc) {
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: wn.model.get("Communication", {"parent": doc.name, "parenttype": "Job Applicant"}),
			parent: cur_frm.fields_dict['thread_html'].wrapper,
			doc: doc,
			recipients: doc.email_id
		})
	},
}