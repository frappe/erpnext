// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Selling Settings", {
	refresh(frm) {
		if (!frm.naming_controller) frm.naming_controller = new erpnext.NamingSeriesController(frm);

		const display = frm.doc.cust_master_name === "Naming Series";
		frm.set_df_property("naming_series_details", "hidden", !display);
		frm.set_df_property("configure", "hidden", !display);

		if (display) {
			frm.naming_controller.load_master_series("Customer", "naming_series_details");
		}

		frm.naming_controller.render_table("transaction_naming_html", get_transactions(frm));
	},

	cust_master_name(frm) {
		const display = frm.doc.cust_master_name === "Naming Series";
		frm.set_df_property("naming_series_details", "hidden", !display);
		frm.set_df_property("configure", "hidden", !display);

		if (display) {
			frm.naming_controller.load_master_series("Customer", "naming_series_details");
		} else {
			frm.doc.naming_series_details = "";
			frm.refresh_field("naming_series_details");
		}

		frm.naming_controller.render_table("transaction_naming_html", get_transactions(frm));
	},

	configure(frm) {
		frm.naming_controller.show_naming_series_dialog("Customer", ({ naming_series_options }) => {
			frm.doc.naming_series_details = naming_series_options;
			frm.refresh_field("naming_series_details");
		});
	},

	after_save(frm) {
		frappe.boot.user.defaults.editable_price_list_rate = frm.doc.editable_price_list_rate;
	},
});

function get_transactions(frm) {
	const transactions = [
		{ label: __("Customer"), doctype: "Customer" },
		{ label: __("Quotation"), doctype: "Quotation" },
		{ label: __("Sales Order"), doctype: "Sales Order" },
		{ label: __("Sales Invoice"), doctype: "Sales Invoice" },
		{ label: __("Delivery Note"), doctype: "Delivery Note" },
	];

	if (frm.doc.cust_master_name !== "Naming Series") {
		return transactions.filter((t) => t.doctype !== "Customer");
	}

	return transactions;
}
