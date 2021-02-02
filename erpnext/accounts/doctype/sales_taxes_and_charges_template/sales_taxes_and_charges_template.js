// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.cscript.tax_table = "Sales Taxes and Charges";

{% include "erpnext/public/js/controllers/accounts.js" %}

frappe.tour['Sales Taxes and Charges Template'] = [
	{
		fieldname: "title",
		title: __("Title"),
		description: __("A name by which you will identify this template. You can change this later."),
	},
	{
		fieldname: "company",
		title: __("Company"),
		description: __("Company for which this tax template will be applicable"),
	},
	{
		fieldname: "is_default",
		title: __("Is this Default?"),
		description: __("Set this template as the default for all sales transactions"),
	},
	{
		fieldname: "taxes",
		title: __("Taxes Table"),
		description: __("You can add a row for a tax rule here. These rules can be applied on the net total, or can be a flat amount."),
	}
];
