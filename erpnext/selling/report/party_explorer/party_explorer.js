frappe.query_reports["Party Explorer"] = {
	filters: [
		{
			fieldname: "party_type",
			label: __("Party Type"),
			fieldtype: "Select",
			options: "Customer\nSupplier",
			default: "Customer",
			reqd: 1,
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
			depends_on: "eval: doc.party_type == 'Customer'",
			description: __("Leave blank to explore every Customer Group from the top level down"),
		},
		{
			fieldname: "supplier_group",
			label: __("Supplier Group"),
			fieldtype: "Link",
			options: "Supplier Group",
			depends_on: "eval: doc.party_type == 'Supplier'",
			description: __("Leave blank to explore every Supplier Group from the top level down"),
		},
	],
};
