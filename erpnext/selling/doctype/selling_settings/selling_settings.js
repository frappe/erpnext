// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Selling Settings', {
	refresh: function(frm) {

	}
});

frappe.tour['Selling Settings'] = [
	{
		fieldname: "cust_master_name",
		title: "Customer Naming By",
		description: __("By default, the Customer Name is set as per the Full Name entered. If you want Customers to be named by a ") + "<a href='https://docs.erpnext.com/docs/user/manual/en/setting-up/settings/naming-series' target='_blank'>Naming Series</a>" + __(" choose the 'Naming Series' option."),
	},
	{
		fieldname: "selling_price_list",
		title: "Default Selling Price List",
		description: __("Configure the default Price List when creating a new Sales transaction. Item prices will be fetched from this Price List.")
	},
	{
		fieldname: "so_required",
		title: "Sales Order Required for Sales Invoice & Delivery Note Creation",
		description: __("If this option is configured 'Yes', ERPNext will prevent you from creating a Sales Invoice or Delivery Note without creating a Sales Order first. This configuration can be overridden for a particular Customer by enabling the 'Allow Sales Invoice Creation Without Sales Order' checkbox in the Customer master.")
	},
	{
		fieldname: "dn_required",
		title: "Delivery Note Required for Sales Invoice Creation",
		description: __("If this option is configured 'Yes', ERPNext will prevent you from creating a Sales Invoice without creating a Delivery Note first. This configuration can be overridden for a particular Customer by enabling the 'Allow Sales Invoice Creation Without Delivery Note' checkbox in the Customer master.")
	}
];
