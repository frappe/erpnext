// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Interview Feedback', {
	onload: function(frm) {
		frm.ignore_doctypes_on_cancel_all = ['Interview'];

		frm.set_query('interview', function() {
			return {
				filters: {
					docstatus: ['!=', 2]
				}
			};
		});
	},

	interview_round: function(frm) {
		frappe.call({
			method: 'erpnext.hr.doctype.interview.interview.get_expected_skill_set',
			args: {
				interview_round: frm.doc.interview_round
			},
			callback: function(r) {
				frm.set_value('skill_assessment', r.message);
			}
		});
	},

	interview: function(frm) {
		frappe.call({
			method: 'erpnext.hr.doctype.interview_feedback.interview_feedback.get_applicable_interviewers',
			args: {
				interview: frm.doc.interview || ''
			},
			callback: function(r) {
				frm.set_query('interviewer', function() {
					return {
						filters: {
							name: ['in', r.message]
						}
					};
				});
			}
		});

	},

	interviewer: function(frm) {
		if (!frm.doc.interview) {
			frappe.throw(__('Select Interview first'));
			frm.set_value('interviewer', '');
		}
	}
});
