// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payroll Settings', {
	encrypt_salary_slips_in_emails: function(frm) {
		let encrypt_state = frm.doc.encrypt_salary_slips_in_emails;
		frm.set_df_property('password_policy', 'reqd', encrypt_state);
	},

	validate: function(frm) {
		let policy = frm.doc.password_policy;
		if (policy) {
			if (policy.includes(' ') || policy.includes('--')) {
				frappe.msgprint(__("Password policy cannot contain spaces or simultaneous hyphens. The format will be restructured automatically"));
			}
			frm.set_value('password_policy', policy.split(new RegExp(" |-", 'g')).filter((token) => token).join('-'));
		}
	},
});

frappe.tour['Payroll Settings'] = [
	{
		fieldname: "payroll_based_on",
		title: "Calculate Payroll Payment Based On",
		description: __("Payment Days in Salary Slip can be calculated based on Leave Application or Attendance records. You can select the option based on which Payment days will be calculated"),
	},
	{
		fieldname: "daily_wages_fraction_for_half_day",
		title: "Daily Wages Fraction for Half Day",
		description: __("Based on this fraction, the salary for Half Day will be calculated. For example, if the value is set as 0.75, the three-fourth salary will be given on half-day attendance.")
	},
	{
		fieldname: "max_working_hours_against_timesheet",
		title: "Max working hours against Timesheet",
		description: __("For salary slips based on the timesheet, you can set the maximum allowed hours against a single timesheet. Set this value to zero to disable this validation.")
	},
	{
		fieldname: "encrypt_salary_slips_in_emails",
		title: "Encrypt Salary Slips in Emails",
		description: __("If Enabled, the salary slip PDF sent to the employee is encrypted using the mentioned Password Policy")
	}
];
