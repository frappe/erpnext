// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Workstation Operating Component", {
	setup(frm) {
		frm.set_query("expense_account", "accounts", function (doc, cdt, cdn) {
			let row = locals[cdt][cdn];
			return {
				filters: { company: row.company, is_group: 0, root_type: "Expense" },
			};
		});
	},
});
