// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.provide("erpnext.accounts.dimensions");

frappe.ui.form.on("Budget", {
	onload: function (frm) {
		frm.set_query("monthly_distribution", function () {
			return {
				filters: {
					fiscal_year: frm.doc.fiscal_year,
				},
			};
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
		frappe.db.get_single_value("Accounts Settings", "use_legacy_budget_controller").then((value) => {
			if (value) {
				frm.get_field("control_action_for_cumulative_expense_section").hide();
			}
		});
	},

	refresh: async function (frm) {
		frm.trigger("toggle_reqd_fields");

		if (!frm.doc.__islocal && frm.doc.docstatus == 1) {
			let exception_role = await frappe.db.get_value(
				"Company",
				frm.doc.company,
				"exception_budget_approver_role"
			);

			const role = exception_role.message.exception_budget_approver_role;

			if (role && frappe.user.has_role(role)) {
				frm.add_custom_button(
					__("Revise Budget"),
					function () {
						frm.events.revise_budget_action(frm);
					},
					__("Actions")
				);
			}
		}
	},

	budget_against: function (frm) {
		frm.trigger("set_null_value");
		frm.trigger("toggle_reqd_fields");
	},

	budget_amount(frm) {
		if (frm.doc.budget_distribution?.length) {
			frm.doc.budget_distribution.forEach((row) => {
				row.amount = flt((row.percent / 100) * frm.doc.budget_amount, 2);
			});
			frm.refresh_field("budget_distribution");
		}
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

	revise_budget_action: function (frm) {
		frappe.confirm(
			__(
				"Are you sure you want to revise this budget? The current budget will be cancelled and a new draft will be created."
			),
			function () {
				frappe.call({
					method: "erpnext.accounts.doctype.budget.budget.revise_budget",
					args: { budget_name: frm.doc.name },
					callback: function (r) {
						if (r.message) {
							frappe.msgprint(__("New revised budget created successfully"));
							frappe.set_route("Form", "Budget", r.message);
						}
					},
				});
			},
			function () {
				frappe.msgprint(__("Revision cancelled"));
			}
		);
	},
});

frappe.ui.form.on("Budget Distribution", {
	amount(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (frm.doc.budget_amount) {
			row.percent = flt((row.amount / frm.doc.budget_amount) * 100, 2);
			frm.refresh_field("budget_distribution");
		}
	},
	percent(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (frm.doc.budget_amount) {
			row.amount = flt((row.percent / 100) * frm.doc.budget_amount, 2);
			frm.refresh_field("budget_distribution");
		}
	},
});
