// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('HR Settings', {
});

frappe.tour['HR Settings'] = [
	{
		fieldname: 'emp_created_by',
		title: 'Employee Naming By',
		description: __('Employee can be named by Employee ID if you assign one, or via Naming Series. Select your preference here.'),
	},
	{
		fieldname: 'standard_working_hours',
		title: 'Standard Working Hours',
		description: __('Enter the Standard Working Hours for a normal work day. These hours will be used in calculations of reports such as Employee Hours Utilization and Project Profitability analysis.'),
	},
	{
		fieldname: 'leave_and_expense_claim_settings',
		title: 'Leave and Expense Clain Settings',
		description: __('Review various other settings related to Employee Leaves and Expense Claim')
	}
];
