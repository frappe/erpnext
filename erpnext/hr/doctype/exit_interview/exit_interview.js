// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Exit Interview', {
	refresh: function(frm) {
		if (!frm.doc.__islocal && !frm.doc.questionnaire_email_sent) {
			frm.add_custom_button(__('Send Exit Questionnaire'), function () {
				frm.trigger('send_exit_questionnaire');
			});
		}
	},

	employee: function(frm) {
		frappe.db.get_value('Employee', frm.doc.employee, 'relieving_date', (message) => {
			if (!message.relieving_date) {
				frappe.throw({
					message: __('Please set the relieving date for employee {0}',
						['<a href="/app/employee/' + frm.doc.employee +'">' + frm.doc.employee + '</a>']),
					title: __('Relieving Date Missing')
				});
			}
		});
	},

	send_exit_questionnaire: function(frm) {
		frappe.db.get_value('HR Settings', 'HR Settings',
			['exit_questionnaire_web_form', 'exit_questionnaire_notification_template'], (r) => {
			if (!r.exit_questionnaire_web_form || !r.exit_questionnaire_notification_template) {
				frappe.throw({
					message: __('Please set {0} and {1} in {2}.',
						['Exit Questionnaire Web Form'.bold(),
						'Notification Template'.bold(),
						'<a href="/app/hr-settings" target="_blank">HR Settings</a>']
					),
					title: __('Settings Missing')
				});
			} else {
				frappe.call({
					method: 'erpnext.hr.doctype.exit_interview.exit_interview.send_exit_questionnaire',
					args: {
						'exit_interview': frm.doc.name
					},
					callback: function(r) {
						if (!r.exc) {
							frm.refresh_field('questionnaire_email_sent');
						}
					}
				});
			}
		});
	}
});
