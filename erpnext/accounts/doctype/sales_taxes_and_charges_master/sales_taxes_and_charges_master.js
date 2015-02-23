// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

{% include "public/js/controllers/accounts.js" %}

cur_frm.cscript.onload = function(doc, cdt, cdn) {
	if(doc.doctype === "Sales Taxes and Charges Master")
		erpnext.add_applicable_territory();
}
