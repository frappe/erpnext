var get_filters = function(){
	return [
		{
			"fieldname":"period",
			"label": "Period",
			"fieldtype": "Select",
			"options": ["Monthly", "Quarterly", "Half-Yearly", "Yearly"].join("\n"),
			"default": "Monthly"
		},
		{
			"fieldname":"based_on",
			"label": "Based On",
			"fieldtype": "Select",
			"options": ["Item", "Item Group", "Supplier", "Supplier Type", "Project"].join("\n"),
			"default": "Item"
		},
		{
			"fieldname":"group_by",
			"label": "Group By",
			"fieldtype": "Select",
			"options": ["Item", "Supplier"].join("\n"),
			"default": ""
		},
		{
			"fieldname":"fiscal_year",
			"label": "Fiscal Year",
			"fieldtype": "Link",
			"options":'Fiscal Year',
			"default": sys_defaults.fiscal_year
		},
		{
			"fieldname":"company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"default": sys_defaults.company
		},
	];
}