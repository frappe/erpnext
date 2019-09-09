// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/loan_management/loan_common.js' %};

frappe.ui.form.on('Loan Application', {

	setup: function(frm) {
		frm.make_methods = {
			'Loan': function() { frm.trigger('create_loan') }
		}
	},

	refresh: function(frm) {
		frm.trigger("toggle_fields");
		frm.trigger("add_toolbar_buttons");
	},
	repayment_method: function(frm) {
		frm.doc.repayment_amount = frm.doc.repayment_periods = ""
		frm.trigger("toggle_fields")
		frm.trigger("toggle_required")
	},
	toggle_fields: function(frm) {
		frm.toggle_enable("repayment_amount", frm.doc.repayment_method=="Repay Fixed Amount per Period")
		frm.toggle_enable("repayment_periods", frm.doc.repayment_method=="Repay Over Number of Periods")
	},
	toggle_required: function(frm){
		frm.toggle_reqd("repayment_amount", cint(frm.doc.repayment_method=='Repay Fixed Amount per Period'))
		frm.toggle_reqd("repayment_periods", cint(frm.doc.repayment_method=='Repay Over Number of Periods'))
	},
	add_toolbar_buttons: function(frm) {
		if (frm.doc.status == "Approved") {

			frappe.db.get_value("Loan Security Pledge", {"loan_application": frm.doc.name}, "name", (r) => {
				if (!r) {
					frm.add_custom_button(__('Loan Security Pledge'), function() {
						frm.trigger('create_loan_security_pledge')
					},__('Create'))
				}
			})

			frm.add_custom_button(__('Loan'), function() {
				frm.trigger('create_loan');
			},__('Create'));
		}
	},

	create_loan: function(frm) {
		frappe.model.open_mapped_doc({
			method: 'erpnext.loan_management.doctype.loan_application.loan_application.create_loan',
			frm: frm
		});
	},

	create_loan_security_pledge: function(frm) {
		frappe.call({
			method: "erpnext.loan_management.doctype.loan_application.loan_application.create_pledge",
			args: {
				loan_application: frm.doc.name
			}
		})
	}
});

frappe.ui.form.on("Proposed Pledge", {
	qty: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.loan_security_price);

		let maximum_amount = 0;

		$.each(frm.doc.proposed_pledges || [], function(i, item){
			maximum_amount += item.amount - (item.amount * item.haircut/100);
		});

		frm.set_value('maximum_loan_amount', maximum_amount);
	}
})
