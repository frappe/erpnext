// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Default Rule', {
	onload: function(frm) {
		frm.events.setup_queries(frm);
	},

	setup_queries: function (frm) {
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_query("income_account", function(doc) {
			return {
				query: "erpnext.controllers.queries.get_income_account",
				filters: {company: doc.company}
			}
		});

		frm.set_query("expense_account", function(doc) {
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: {company: doc.company}
			}
		});

		frm.set_query("claim_customer", erpnext.queries.customer);
		frm.set_query('default_supplier', erpnext.queries.supplier);
		frm.set_query("item_code", function () {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: {'include_disabled': 1, 'include_templates': 1}
			};
		});

		$.each(['selling_cost_center', 'buying_cost_center'], function (i, f) {
			frm.set_query(f, function(doc) {
				return {
					filters: {
						'company': doc.company,
						"is_group": 0
					}
				}
			});
		});
	},
});
