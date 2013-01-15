// For license information, please see license.txt

cur_frm.cscript = {
	refresh: function(doc) {
		cur_frm.cscript.make_listing(doc);
	},
	make_listing: function(doc) {
		cur_frm.communication_view = new wn.views.CommunicationList({
			list: wn.model.get("Communication", {"job_applicant": doc.name}),
			parent: cur_frm.fields_dict['thread_html'].wrapper,
			doc: doc,
			recipients: doc.email_id
		})
	},
}