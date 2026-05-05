// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Selling Settings", {
	refresh(frm) {
		frm._naming_ctrl =
			frm._naming_ctrl ||
			new erpnext.NamingSeriesController(frm, {
				master_naming_field: "cust_master_name",
				master_doctype: "Customer",
				details_field: "naming_series_details",
				configure_button: "configure",
				table_field: "transaction_naming_html",
				transactions: [
					{ label: __("Customer"), doctype: "Customer" },
					{ label: __("Quotation"), doctype: "Quotation" },
					{ label: __("Sales Order"), doctype: "Sales Order" },
					{ label: __("Sales Invoice"), doctype: "Sales Invoice" },
					{ label: __("Delivery Note"), doctype: "Delivery Note" },
					{ label: __("Payment Entry"), doctype: "Payment Entry" },
					{ label: __("POS Invoice"), doctype: "POS Invoice" },
				],
			});

		frm._naming_ctrl.refresh();
	},

	cust_master_name(frm) {
		frm._naming_ctrl?.on_master_naming_change();
	},

	configure(frm) {
		frm._naming_ctrl?.show_naming_series_dialog("Customer");
	},

	after_save(frm) {
		frappe.boot.user.defaults.editable_price_list_rate = frm.doc.editable_price_list_rate;
	},
});
