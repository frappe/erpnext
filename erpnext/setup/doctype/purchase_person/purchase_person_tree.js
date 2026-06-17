frappe.treeview_settings["Purchase Person"] = {
	fields: [
		{
			fieldtype: "Data",
			fieldname: "purchase_person_name",
			label: __("New Purchase Person Name"),
			reqd: true,
		},
		{
			fieldtype: "Link",
			fieldname: "employee",
			label: __("Employee"),
			options: "Employee",
			description: __("Please enter Employee Id of this purchase person"),
		},
		{
			fieldtype: "Check",
			fieldname: "is_group",
			label: __("Group Node"),
			description: __("Further nodes can be only created under 'Group' type nodes"),
		},
	],
};
