// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("company", "default_receivable_account", "debit_to");
cur_frm.add_fetch("company", "default_income_account", "against_income_account");
cur_frm.add_fetch("company", "cost_center", "cost_center");

frappe.ui.form.on('Fee Structure', {
	onload: function(frm) {
		frm.set_query("debit_to", function(doc) {
			return {
				filters: {
					'account_type': 'Receivable',
					'is_group': 0,
					'company': doc.company
				}
			};
		});
	}
});

frappe.ui.form.on("Fee Component", {
	amount: function(frm) {
		var total_amount = 0;
		for(var i=0;i<frm.doc.components.length;i++) {
			total_amount += frm.doc.components[i].amount;
		}
		frm.set_value("total_amount", total_amount);
	}
});