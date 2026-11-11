// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Subscription Plan", {
	setup: function (frm) {
		if (frm.fields_dict.payment_account) {
			frm.set_query("payment_account", function () {
				return {
					query: "erpnext.accounts.doctype.payment_request.payment_request.get_payment_account",
					filters: {
						payment_gateway: frm.doc.payment_gateway,
					},
				};
			});
		}
	},

	payment_gateway(frm) {
		frm.set_value("payment_account", null);
	},

	price_determination: function (frm) {
		frm.toggle_reqd("cost", frm.doc.price_determination === "Fixed rate");
		frm.toggle_reqd("price_list", frm.doc.price_determination === "Based on price list");
	},

	subscription_plan: function (frm) {
		erpnext.utils.check_payments_app();
	},
});
