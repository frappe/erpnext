// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Budget", {
	onload: function (frm) {
		frm.set_query("account", "accounts", function () {
			return {
				filters: {
					company: frm.doc.company,
					report_type: "Profit and Loss",
					is_group: 0,
				},
			};
		});

		frm.set_query("monthly_distribution", function () {
			return {
				filters: {
					fiscal_year: frm.doc.fiscal_year,
				},
			};
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	refresh: function (frm) {
		frm.trigger("toggle_reqd_fields");
	},

	budget_against: function (frm) {
		frm.trigger("set_null_value");
		frm.trigger("toggle_reqd_fields");
	},

	set_null_value: function (frm) {
		if (frm.doc.budget_against == "Cost Center") {
			frm.set_value("project", null);
		} else {
			frm.set_value("cost_center", null);
		}
	},

	toggle_reqd_fields: function (frm) {
		frm.toggle_reqd("cost_center", frm.doc.budget_against == "Cost Center");
		frm.toggle_reqd("project", frm.doc.budget_against == "Project");
	},
});
