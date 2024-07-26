// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Item Tax Template", {
	setup: function (frm) {
		frm.set_query("tax_type", "taxes", function (doc) {
			return {
				filters: [
					["Account", "company", "=", frm.doc.company],
					["Account", "is_group", "=", 0],
					[
						"Account",
						"account_type",
						"in",
						[
							"Tax",
							"Chargeable",
							"Income Account",
							"Expense Account",
							"Expenses Included In Valuation",
						],
					],
				],
			};
		});
	},
	company: function (frm) {
		frm.set_query("tax_type", "taxes", function (doc) {
			return {
				filters: [
					["Account", "company", "=", frm.doc.company],
					["Account", "is_group", "=", 0],
					[
						"Account",
						"account_type",
						"in",
						[
							"Tax",
							"Chargeable",
							"Income Account",
							"Expense Account",
							"Expenses Included In Valuation",
						],
					],
				],
			};
		});
	},
});
