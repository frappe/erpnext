// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Asset Revaluation", {
	setup: function (frm) {
		frm.add_fetch("company", "cost_center", "cost_center");

		frm.set_query("cost_center", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0
				}
			}
		});

		frm.set_query("asset", function () {
			return {
				filters: {
					calculate_depreciation: 1,
					docstatus: 1
				}
			};
		});

		frm.set_query("serial_no", function () {
			return {
				filters: {
					asset: frm.doc.asset,
				}
			};
		});
	},
});
