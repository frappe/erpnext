// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Share Transfer", {
	refresh(frm) {
		frm.disable_form();
		frm.set_intro(
			__("This is a historical Share Transfer. New share activity must use Share Transaction."),
			"yellow"
		);
	},
});
