// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Buying Settings", {
	refresh(frm) {
		frm.naming_controller =
			frm.naming_controller ||
			new erpnext.NamingSeriesController(frm, {
				master_naming_field: "supp_master_name",
				master_doctype: "Supplier",
				details_field: "naming_series_details",
				configure_button: "configure",
				table_field: "transaction_naming_html",
				transactions: [
					{ label: __("Supplier"), doctype: "Supplier" },
					{ label: __("Material Request"), doctype: "Material Request" },
					{ label: __("Request for Quotation"), doctype: "Request for Quotation" },
					{ label: __("Supplier Quotation"), doctype: "Supplier Quotation" },
					{ label: __("Purchase Order"), doctype: "Purchase Order" },
					{ label: __("Purchase Invoice"), doctype: "Purchase Invoice" },
					{ label: __("Purchase Receipt"), doctype: "Purchase Receipt" },
				],
			});
		frm.naming_controller.refresh();
	},

	supp_master_name(frm) {
		frm.naming_controller?.on_master_naming_change();
	},

	configure(frm) {
		frm.naming_controller?.show_naming_series_dialog("Supplier");
	},
});

frappe.tour["Buying Settings"] = [
	{
		fieldname: "supp_master_name",
		title: "Supplier Naming By",
		description: __(
			"By default, the Supplier Name is set as per the Supplier Name entered. If you want Suppliers to be named by a <a href='https://docs.erpnext.com/docs/user/manual/en/setting-up/settings/naming-series' target='_blank'>Naming Series</a> choose the 'Naming Series' option."
		),
	},
	{
		fieldname: "buying_price_list",
		title: "Default Buying Price List",
		description: __(
			"Configure the default Price List when creating a new Purchase transaction. Item prices will be fetched from this Price List."
		),
	},
	{
		fieldname: "po_required",
		title: "Purchase Order Required for Purchase Invoice & Receipt Creation",
		description: __(
			"If this option is configured 'Yes', ERPNext will prevent you from creating a Purchase Invoice or Receipt without creating a Purchase Order first. This configuration can be overridden for a particular supplier by enabling the 'Allow Purchase Invoice Creation Without Purchase Order' checkbox in the Supplier master."
		),
	},
	{
		fieldname: "pr_required",
		title: "Purchase Receipt Required for Purchase Invoice Creation",
		description: __(
			"If this option is configured 'Yes', ERPNext will prevent you from creating a Purchase Invoice without creating a Purchase Receipt first. This configuration can be overridden for a particular supplier by enabling the 'Allow Purchase Invoice Creation Without Purchase Receipt' checkbox in the Supplier master."
		),
	},
];
