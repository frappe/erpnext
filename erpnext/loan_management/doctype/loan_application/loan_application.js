// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

{% include 'erpnext/loan_management/loan_common.js' %};

frappe.ui.form.on('Loan Application', {

	setup: function(frm) {
		frm.make_methods = {
			'Loan': function() { frm.trigger('create_loan') },
			'Loan Security Pledge': function() { frm.trigger('create_loan_security_pledge') },
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

			if (frm.doc.is_secured_loan) {
				frappe.db.get_value("Loan Security Pledge", {"loan_application": frm.doc.name, "docstatus": 1}, "name", (r) => {
					if (Object.keys(r).length === 0) {
						frm.add_custom_button(__('Loan Security Pledge'), function() {
							frm.trigger('create_loan_security_pledge');
						},__('Create'))
					}
				});
			}

			frappe.db.get_value("Loan", {"loan_application": frm.doc.name, "docstatus": 1}, "name", (r) => {
				if (Object.keys(r).length === 0) {
					frm.add_custom_button(__('Loan'), function() {
						frm.trigger('create_loan');
					},__('Create'))
				} else {
					frm.set_df_property('status', 'read_only', 1);
				}
			});
		}
	},
	create_loan: function(frm) {
		if (frm.doc.status != "Approved") {
			frappe.throw(__("Cannot create loan until application is approved"));
		}

		frappe.model.open_mapped_doc({
			method: 'erpnext.loan_management.doctype.loan_application.loan_application.create_loan',
			frm: frm
		});
	},
	create_loan_security_pledge: function(frm) {

		if(!frm.doc.is_secured_loan) {
			frappe.throw(__("Loan Security Pledge can only be created for secured loans"));
		}

		frappe.call({
			method: "erpnext.loan_management.doctype.loan_application.loan_application.create_pledge",
			args: {
				loan_application: frm.doc.name
			},
			callback: function(r) {
				frappe.set_route("Form", "Loan Security Pledge", r.message);
			}
		})
	},
	is_term_loan: function(frm) {
		frm.set_df_property('repayment_method', 'hidden', 1 - frm.doc.is_term_loan);
		frm.set_df_property('repayment_method', 'reqd', frm.doc.is_term_loan);
	},
	is_secured_loan: function(frm) {
		frm.set_df_property('proposed_pledges', 'reqd', frm.doc.is_secured_loan);
	},

	calculate_amounts: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.qty) {
			frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.loan_security_price);
			frappe.model.set_value(cdt, cdn, 'post_haircut_amount', cint(row.amount - (row.amount * row.haircut/100)));
		} else if (row.amount) {
			frappe.model.set_value(cdt, cdn, 'qty', cint(row.amount / row.loan_security_price));
			frappe.model.set_value(cdt, cdn, 'amount', row.qty * row.loan_security_price);
			frappe.model.set_value(cdt, cdn, 'post_haircut_amount', cint(row.amount - (row.amount * row.haircut/100)));
		}

		let maximum_amount = 0;

		$.each(frm.doc.proposed_pledges || [], function(i, item){
			maximum_amount += item.post_haircut_amount;
		});

		if (flt(maximum_amount)) {
			frm.set_value('maximum_loan_amount', flt(maximum_amount));
		}
	}
});

frappe.ui.form.on("Proposed Pledge", {
	loan_security: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.loan_security) {
			frappe.call({
				method: "erpnext.loan_management.doctype.loan_security_price.loan_security_price.get_loan_security_price",
				args: {
					loan_security: row.loan_security
				},
				callback: function(r) {
					frappe.model.set_value(cdt, cdn, 'loan_security_price', r.message);
					frm.events.calculate_amounts(frm, cdt, cdn);
				}
			})
		}
	},

	amount: function(frm, cdt, cdn) {
		frm.events.calculate_amounts(frm, cdt, cdn);
	},

	qty: function(frm, cdt, cdn) {
		frm.events.calculate_amounts(frm, cdt, cdn);
	},
})
