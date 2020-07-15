// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Income Tax Slab', {

});

frappe.tour['Income Tax Slab'] = [
	{
		fieldname: "__newname",
		title: "Enter Name",
		description: __("Enter name for your Income Tax Slab"),
	},
	{
		fieldname: "effective_from",
		title: "Effective From",
		description: __("Enter date from which it will be effective")
	},
	{
		fieldname: "allow_tax_exemption",
		title: "Allow Tax Exemption",
		description: __("Tax Exemption will be applicable if checked.")
	},
	{
		fieldname: "slabs",
		title: "Taxable Salary Slabs",
		description: __("To define slab, From Amount, To Amount should and Percent Deductions is required. The tax slab can be applicable based on specific conditions")
	}
];