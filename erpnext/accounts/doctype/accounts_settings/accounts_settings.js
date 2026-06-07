// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Accounts Settings", {
	refresh: function (frm) {
		frm.set_query("document_type", "repost_allowed_types", function (doc, cdt, cdn) {
			return {
				filters: {
					name: ["in", frappe.boot.sysdefaults.repost_allowed_doctypes],
				},
			};
		});
		if (!frm.naming_controller) frm.naming_controller = new erpnext.NamingSeriesController(frm);

		frm.naming_controller.render_table("transaction_naming_html", get_transactions(frm));
	},
	enable_immutable_ledger: function (frm) {
		if (!frm.doc.enable_immutable_ledger) {
			return;
		}

		let msg = __("Enabling this will change the way how cancelled transactions are handled.");
		msg += " ";
		msg += __("Please enable only if the understand the effects of enabling this.");
		msg += "<br>";
		msg += __("Do you still want to enable immutable ledger?");

		frappe.confirm(
			msg,
			() => {},
			() => {
				frm.set_value("enable_immutable_ledger", 0);
			}
		);
	},

	add_taxes_from_taxes_and_charges_template(frm) {
		toggle_tax_settings(frm, "add_taxes_from_taxes_and_charges_template");
	},

	add_taxes_from_item_tax_template(frm) {
		toggle_tax_settings(frm, "add_taxes_from_item_tax_template");
	},
});

function toggle_tax_settings(frm, field_name) {
	if (frm.doc[field_name]) {
		const other_field =
			field_name === "add_taxes_from_item_tax_template"
				? "add_taxes_from_taxes_and_charges_template"
				: "add_taxes_from_item_tax_template";
		frm.set_value(other_field, 0);
	}
}

function get_transactions(frm) {
	const transactions = [
		{ label: __("Journal Entry"), doctype: "Journal Entry" },
		{ label: __("Payment Entry"), doctype: "Payment Entry" },
		{ label: __("Purchase Invoice"), doctype: "Purchase Invoice" },
		{ label: __("Purchase Order"), doctype: "Purchase Order" },
		{ label: __("Purchase Receipt"), doctype: "Purchase Receipt" },
		{ label: __("Sales Invoice"), doctype: "Sales Invoice" },
	];

	return transactions;
}
