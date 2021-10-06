// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Request', {
	setup: function(frm) {
		frm.set_query("approver", function() {
			return {
				query: "erpnext.hr.doctype.department_approver.department_approver.get_approvers",
				filters: {
					employee: frm.doc.employee,
					doctype: frm.doc.doctype
				}
			};
		});
		frm.set_query("employee", erpnext.queries.employee);
	},
	from_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.from_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("from_date_nepal", resp.message)
				}
			}
		})
	},
	to_date: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.to_date
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("to_date_nepal", resp.message)
				}
			}
		})
	
	
	}
});
