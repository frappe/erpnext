// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// For license information, please see license.txt

cur_frm.cscript = {
	refresh: function(doc) {
		cur_frm.set_intro("");
		if(doc.extract_emails) {
			cur_frm.set_intro(wn._("Active: Will extract emails from ") + doc.email_id);
		} else {
			cur_frm.set_intro(wn._("Not Active"));
		}
	}
}