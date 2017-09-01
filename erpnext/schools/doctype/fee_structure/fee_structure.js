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
	},

	refresh: function(frm) {
		if(frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Make Fee Schedule"), function() {
				frm.events.make_fee_schedule(frm);
			});
		}
	},

	make_fee_schedule: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.schools.doctype.fee_structure.fee_structure.make_fee_schedule",
			frm: frm
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