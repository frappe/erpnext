// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Driver", {
	setup: function (frm) {
		frm.set_query("transporter", function () {
			return {
				filters: {
					is_transporter: 1,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.set_query("address", function () {
			return {
				filters: {
					is_your_company_address: !frm.doc.transporter ? 1 : 0,
				},
			};
		});
	},

	transporter: function (frm, cdt, cdn) {
		// this assumes that supplier's address has same title as supplier's name
		if (!frm.doc.transporter) return;
		frappe.db
			.get_value("Address", { address_title: frm.doc.transporter }, "name")
			.then((r) => {
				if (r && r.message && r.message.name) {
					frappe.model.set_value(cdt, cdn, "address", r.message.name);
				} else {
					frappe.model.set_value(cdt, cdn, "address", "");
				}
			})
			.catch((err) => {
				console.log(err);
			});
	},
});
