// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on(cur_frm.doctype, {
	refresh: function(frm) {
		if (!frappe.boot.active_domains.includes("Non Profit")) {
			frm.set_df_property('applicant_type', 'options', ['Employee', 'Customer']);
			frm.refresh_field('applicant_type');
		}

		if (['Loan Disbursement', 'Loan Repayment', 'Loan Interest Accrual', 'Loan Write Off'].includes(frm.doc.doctype)
			&& frm.doc.docstatus > 0) {

			frm.add_custom_button(__("Accounting Ledger"), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					company: frm.doc.company,
					from_date: moment(frm.doc.posting_date).format('YYYY-MM-DD'),
					to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
					show_cancelled_entries: frm.doc.docstatus === 2
				};

				frappe.set_route("query-report", "General Ledger");
			},__("View"));
		}
	},
	applicant: function(frm) {
		if (!["Loan Application", "Loan"].includes(frm.doc.doctype)) {
			return;
		}

		if (frm.doc.applicant) {
			frappe.model.with_doc(frm.doc.applicant_type, frm.doc.applicant, function() {
				var applicant = frappe.model.get_doc(frm.doc.applicant_type, frm.doc.applicant);
				frm.set_value("applicant_name",
					applicant.employee_name || applicant.member_name);
			});
		}
		else {
			frm.set_value("applicant_name", null);
		}
	}
});