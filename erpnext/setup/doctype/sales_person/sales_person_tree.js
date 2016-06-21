frappe.treeview_settings["Sales Person"] = {
	fields: [
		{fieldtype:'Data', fieldname: 'name_field',
			label:__('New Sales Person Name'), reqd:true},
		{fieldtype:'Link', fieldname:'employee',
			label:__('Employee'), options:'Employee',
			description: __("Please enter Employee Id of this sales person")},
		{fieldtype:'Select', fieldname:'is_group', label:__('Group Node'), options:'No\nYes',
			description: __("Further nodes can be only created under 'Group' type nodes")}
	],
}