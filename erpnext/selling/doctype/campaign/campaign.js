// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Campaign", "refresh", function(frm) {
	erpnext.toggle_naming_series();
	if(frm.doc.__islocal) {
		frm.toggle_display("naming_series", frappe.boot.sysdefaults.campaign_naming_by=="Naming Series");
	}
})
