frappe.ui.form.on("Leave Type", {
	refresh: function(frm) {
	}
});


frappe.tour["Leave Type"] = [
	{
		fieldname: "max_leaves_allowed",
		title: "Maximum Leave Allocation Allowed",
		description: __("This field allows you to set the maximum number of leaves that can be allocated annually for this Leave Type while creating the Leave Policy")
	},
	{
		fieldname: "max_continuous_days_allowed",
		title: "Maximum Consecutive Leaves Allowed",
		description: __("This field allows you to set the maximum number of consecutive leaves an Employee can apply for.")
	},
	{
		fieldname: "is_optional_leave",
		title: "Is Optional Leave",
		description: __("Optional Leaves are holidays that Employees can choose to avail from a list of holidays published by the company.")
	},
	{
		fieldname: "is_compensatory",
		title: "Is Compensatory Leave",
		description: __("Leaves you can avail against a holiday you worked on. You can claim Compensatory Off Leave using Compensatory Leave request. Click") + " <a href='https://docs.erpnext.com/docs/v13/user/manual/en/human-resources/compensatory-leave-request' target='_blank'>here</a> " + __('to know more')
	},
	{
		fieldname: "allow_encashment",
		title: "Allow Encashment",
		description: __("From here, you can enable encashment for the balance leaves.")
	},
	{
		fieldname: "is_earned_leave",
		title: "Is Earned Leaves",
		description: __("Earned Leaves are leaves earned by an Employee after working with the company for a certain amount of time. Enabling this will allocate leaves on pro-rata basis by automatically updating Leave Allocation for leaves of this type at intervals set by 'Earned Leave Frequency.")
	}
];