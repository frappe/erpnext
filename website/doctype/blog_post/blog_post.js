// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	if(!doc.__islocal && doc.published && !doc.email_sent) {
		cur_frm.add_custom_button('Email Subscribers', function() {
			$c_obj(make_doclist(doc.doctype, doc.name), 'send_emails', '', function(r) {
				cur_frm.refresh();
			});
		})
	}
}