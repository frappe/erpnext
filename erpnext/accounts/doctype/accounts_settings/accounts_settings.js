// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Accounts Settings", {
	refresh: function (frm) {},
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

	drop_ar_procedures: function (frm) {
		frm.call({
			doc: frm.doc,
			method: "drop_ar_sql_procedures",
			callback: function (r) {
				frappe.show_alert(__("Procedures dropped"), 5);
			},
		});
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
