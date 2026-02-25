// Copyright (c) 2018, Hash Include Solutions FZC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subscription Plan", {
	price_determination: function (frm) {
		frm.toggle_reqd("cost", frm.doc.price_determination === "Fixed rate");
		frm.toggle_reqd("price_list", frm.doc.price_determination === "Based on price list");
	},

	subscription_plan: function (frm) {
		perceptrons.utils.check_payments_app();
	},
});
