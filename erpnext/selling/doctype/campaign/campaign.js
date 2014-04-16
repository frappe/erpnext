// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Campaign", "refresh", function(frm) {
	erpnext.hide_naming_series();
	if(frappe.boot.sysdefaults.campaign_naming_by!="Naming Series") {
		hide_field("naming_series");
	}
})
