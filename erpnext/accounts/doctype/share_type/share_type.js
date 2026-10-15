// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Share Type", {
	refresh(frm) {
		frm.disable_form();
		frm.set_intro(__("This is a historical Share Type. Create a Share Class instead."), "yellow");
	},
});
