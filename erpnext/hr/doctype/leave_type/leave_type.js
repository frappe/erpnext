frappe.ui.form.on("Leave Type", {
	refresh: function(frm) {
	}
});

frappe.tour['Leave Type'] = [
	{
		fieldname: "leave_type_name",
		title: "Leave Type Name",
		description: __("Name you Leave Type."),
	},
	{
		fieldname: "is_carry_forward",
		title: "Is Carry Forward",
		description: __("If checked, the balance leaves of this Leave Type will be carried forward to the next allocation period.")
	},
	{
		fieldname: "is_lwp",
		title: "Is Leave Without Pay",
		description: __("This ensures that the Leave Type will be treated as leaves without pay and salary will get deducted for this Leave Type.")
	},
	{
		fieldname: "include_holiday",
		title: "Include holidays within leaves as leaves",
		description: __("enable this, if you wish to count holidays within leaves as a ‘leave’")
	},
	{
		fieldname: "is_compensatory",
		title: "Is Compensatory",
		description: __("Compensatory leaves are leaves granted for working overtime or on holidays, normally compensated as an encashable leave.")
	},
	{
		fieldname: "allow_encashment",
		title: "Allow Encashment",
		description: __("It is possible that Employees can receive cash from their Employer for unused leaves granted to them in a Leave Period. Read More about ") + "<a href='https://docs.erpnext.com/docs/user/manual/en/human-resources/leave-type#21-leave-encashment' target='_blank'>" +__("Leave Encashment.")+ "</a>"
	},
	{
		fieldname: "is_earned_leave",
		title: "Is Earned Leave",
		description: __("Earned Leaves are leaves earned by an Employee after working with the company for a certain amount of time.") + "<a href='https://docs.erpnext.com/docs/user/manual/en/human-resources/leave-type#22-earned-leave' target='_blank'>" +__("Earned Leaves.")+ "</a>"
	},
];
