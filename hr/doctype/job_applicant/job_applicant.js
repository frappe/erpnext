// For license information, please see license.txt

cur_frm.cscript = {
	refresh: function(doc) {
		cur_frm.set_intro("");
		if(doc.extract_emails) {
			cur_frm.set_intro(wn._("Active: Will extract emails from ") + doc.email_id);
		} else {
			cur_frm.set_intro(wn._("Not Active"));
		}
		cur_frm.cscript.make_listing(doc);
	},
	make_listing: function(doc) {
		var wrapper = cur_frm.fields_dict['thread_html'].wrapper;
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: comm_list,
			parent: wn.model.get("Communication", {"job_applicant": doc.name}),
			doc: doc,
			recipients: doc.email_id
		})
	},
}