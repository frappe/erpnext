// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt


cur_frm.add_fetch("bank_account", "company", "company");
cur_frm.cscript.onload = function(doc, cdt, cdn){
	cur_frm.set_intro('<i class="icon-question" /> ' + 
		wn._("Update clearance date of Journal Entries marked as 'Bank Vouchers'"))
}
