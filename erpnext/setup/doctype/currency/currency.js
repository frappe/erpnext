// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.refresh = function(doc) {
	cur_frm.set_intro("");
	if(!cur_frm.doc.enabled) {
		cur_frm.set_intro(__("This Currency is disabled. Enable to use in transactions"))
	}
}