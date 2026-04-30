// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Selling Settings", {
	refresh(frm) {
		const display = frm.doc.cust_master_name === "Naming Series";
		frm.set_df_property("naming_series_details", "hidden", !display);
		frm.set_df_property("configure", "hidden", !display);
		if (display) {
			find_naming_series("Customer", "naming_series_details", frm);
		}
		load_default_naming_series(frm);
	},
	cust_master_name(frm) {
		const display = frm.doc.cust_master_name === "Naming Series";
		frm.set_df_property("naming_series_details", "hidden", !display);
		frm.set_df_property("configure", "hidden", !display);
		if (display) {
			find_naming_series("Customer", "naming_series_details", frm);
		} else {
			frm.set_value("naming_series_details", "");
		}
	},

	configure(frm) {
		show_naming_series_dialog("Customer", frm);
	},

	after_save(frm) {
		frappe.boot.user.defaults.editable_price_list_rate = frm.doc.editable_price_list_rate;
	},
});

function show_naming_series_dialog(doctype, frm) {
	if (!frm._naming_series_dialog) {
		frm._naming_series_dialog = new erpnext.NamingSeriesDialog({
			doctype: doctype,
			title: __("Naming Series for {0}", [__(doctype)]),
			on_update: ({ naming_series_options }) => {
				frm.set_value("naming_series_details", naming_series_options);
			},
		});
	}
	frm._naming_series_dialog.show();
}
function find_naming_series(doctype, field, frm) {
	frappe.model.with_doctype(doctype, () => {
		const meta = frappe.get_meta(doctype);
		const naming_df = (meta?.fields || []).find((df) => df.fieldname === "naming_series");
		const options = naming_df?.options || "";
		const series_list = options
			.split("\n")
			.map((s) => s.trim())
			.filter(Boolean);

		frm.doc[field] = series_list.length ? series_list.join("\n") : __("No naming series defined");

		frm.refresh_field(field);
	});
}

function load_default_naming_series(frm) {
	let transactions = [
		{ label: __("Customer"), doctype: "Customer" },
		{ label: __("Quotation"), doctype: "Quotation" },
		{ label: __("Sales Order"), doctype: "Sales Order" },
		{ label: __("Sales Invoice"), doctype: "Sales Invoice" },
		{ label: __("Delivery Note"), doctype: "Delivery Note" },
		{ label: __("Payment Entry"), doctype: "Payment Entry" },
		{ label: __("POS Invoice"), doctype: "POS Invoice" },
	];

	if (frm.doc.cust_master_name !== "Naming Series") {
		transactions = transactions.filter((t) => t.doctype !== "Customer");
	}
	new erpnext.NamingSeriesTable({
		frm: frm,
		fieldname: "transaction_naming_html",
		transactions: transactions,
	}).render();
}
