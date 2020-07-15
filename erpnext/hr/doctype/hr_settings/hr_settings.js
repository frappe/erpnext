// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('HR Settings', {
	restrict_backdated_leave_application: function(frm) {
		frm.toggle_reqd("role_allowed_to_create_backdated_leave_application", frm.doc.restrict_backdated_leave_application);
	}
});


frappe.tour['HR Settings'] = [
	{
		fieldname: "retirement_age",
		title: "Retirement Age",
		description: __("You can enter the retirement age (in years) for your employees"),
	},
	{
		fieldname: "emp_created_by",
		title: "Naming for Employee Records",
		description: __("The naming for employee documents can be based on Naming Series, Employee Name and Full Name.")
	},
	{
		fieldname: "expense_approver_mandatory_in_expense_claim",
		title: "Expense Approver Mandatory In Expense Claim",
		description: __("In Expense Claim Document the 'Expense Approver' field is set to mandatory on checking this option")
	},
	{
		fieldname: "leave_approver_mandatory_in_leave_application",
		title: "Leave Approver Mandatory In Leave Application",
		description: __("In Leave Application document the 'Leave Approver' field is set to mandatory on checking this option")
	},
	{
		fieldname: "auto_leave_encashment",
		title: "Auto Leave Encashment",
		description: __("If checked, the system generates a draft Leave Encashment record on the expiry of the leave allocation for all encashable Leave Types")
	},
	{
		fieldname: "restrict_backdated_leave_application",
		title: "Restrict Backdated Leave Application",
		description: __("If checked, the system will not allow making a backdated leave application.")
	},
];