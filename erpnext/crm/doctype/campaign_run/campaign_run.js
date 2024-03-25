// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Campaign Run", {
	campaign_run_for: function (frm) {
		frm.set_value("recipient", "");
	},
});
