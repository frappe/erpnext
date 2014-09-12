// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include 'controllers/js/contact_address_common.js' %};

cur_frm.email_field = "email_id";
cur_frm.cscript.hide_dialog = function() {
	if(cur_frm.contact_list)
		cur_frm.contact_list.run();
}
