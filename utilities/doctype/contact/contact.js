// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

wn.require('app/controllers/js/contact_address_common.js');

cur_frm.cscript.refresh = function(doc) {
	cur_frm.communication_view = new wn.views.CommunicationList({
		list: wn.model.get("Communication", {"parent": doc.name, "parenttype": "Contact"}),
		parent: cur_frm.fields_dict.communication_html.wrapper,
		doc: doc,
		recipients: doc.email_id
	});
}

cur_frm.cscript.hide_dialog = function() {
	if(cur_frm.contact_list)
		cur_frm.contact_list.run();
}