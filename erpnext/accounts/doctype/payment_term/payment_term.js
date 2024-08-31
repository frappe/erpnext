// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on("Payment Term", {
	setup(frm) {
		frm.make_methods = {
			"Sales Invoice": () => {
				open_form(frm, "Sales Invoice", "Payment Schedule", "payment_schedule");
			},
			"Sales Order": () => {
				open_form(frm, "Sales Order", "Payment Schedule", "payment_schedule");
			},
			Quotation: () => {
				open_form(frm, "Quotation", "Payment Schedule", "payment_schedule");
			},
			"Purchase Invoice": () => {
				open_form(frm, "Purchase Invoice", "Payment Schedule", "payment_schedule");
			},
			"Purchase Order": () => {
				open_form(frm, "Purchase Order", "Payment Schedule", "payment_schedule");
			},
			"Payment Terms Template": () => {
				open_form(frm, "Payment Terms Template", "Payment Terms Template Detail", "terms");
			},
		};
	},
	onload(frm) {
		frm.trigger("set_dynamic_description");
	},
	discount(frm) {
		frm.trigger("set_dynamic_description");
	},
	discount_type(frm) {
		frm.trigger("set_dynamic_description");
	},
	set_dynamic_description(frm) {
		if (frm.doc.discount) {
			let description = __("{0}% of total invoice value will be given as discount.", [
				frm.doc.discount,
			]);
			if (frm.doc.discount_type == "Amount") {
				description = __("{0} will be given as discount.", [frm.doc.discount]);
			}
			frm.set_df_property("discount", "description", description);
		}
	},
});

function open_form(frm, doctype, child_doctype, parentfield) {
	frappe.model.with_doctype(doctype, () => {
		let new_doc = frappe.model.get_new_doc(doctype);
		let new_child_doc = frappe.model.add_child(new_doc, child_doctype, parentfield);

		frappe.run_serially([
			() => frappe.ui.form.make_quick_entry(doctype, null, null, new_doc),
			() => {
				frappe.flags.ignore_company_party_validation = true;
				frappe.model.set_value(child_doctype, new_child_doc.name, "payment_term", frm.doc.name);
			},
		]);
	});
}
