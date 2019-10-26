// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Loan Security Unpledge', {
	refresh: function(frm) {

		frm.set_query("against_pledge", "securities", () => {
			return {
				filters : [["status", "in", ["Pledged", "Partially Pledged"]]]
			}
		});

		if (frm.doc.docstatus == 1 && frm.doc.status == "Requested") {
			frm.add_custom_button("Approve", function(){
				frappe.call({
					method: "erpnext.loan_management.doctype.loan_security_unpledge.loan_security_unpledge.approve_unpledge_request",
					args: {
						loan: frm.doc.loan,
						unpledge_request: frm.doc.name,
						unpledge_type: frm.doc.unpledge_type
					},
					callback: function() {
						frm.reload_doc();
					}
				});
			});
		}
	}
});
