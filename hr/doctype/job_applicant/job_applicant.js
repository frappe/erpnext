
cur_frm.cscript.refresh = function(doc, cdt, cdn) {
	erpnext.hide_naming_series();
	cur_frm.communication_view = new wn.views.CommunicationList({
		list: wn.model.get("Communication", {"job_applicant": doc.name}),
		parent: cur_frm.fields_dict.communication_html.wrapper,
		doc: doc,
		recipients: doc.email_id
	})
}