frappe.query_reports["Customer Group Explorer"] = {
	filters: [
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
			description: __("Leave blank to explore every Customer Group from the top level down"),
		},
	],
};
