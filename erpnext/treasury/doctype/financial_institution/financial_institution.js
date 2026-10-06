// Copyright (c) 2026, Aagnya Mistry and contributors
// For license information, please see license.txt

frappe.ui.form.on("Financial Institution", {
	setup(frm) {
		// once saved, only contacts linked to this institution are offered
		frm.set_query("primary_contact", () => {
			if (frm.is_new()) return {};
			return {
				query: "frappe.contacts.doctype.contact.contact.contact_query",
				filters: { link_doctype: frm.doctype, link_name: frm.doc.name },
			};
		});
	},

	refresh(frm) {
		// a contact created from here is linked to this institution
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: frm.doctype };

		// named by this field, which Frappe hides once saved; keep it visible, rename via the title
		frm.toggle_display("institution_name", true);
		frm.set_df_property("institution_name", "read_only", frm.is_new() ? 0 : 1);

		// contacts link to a saved institution, so they are shown once it exists
		frm.toggle_display("contact_section", !frm.is_new());
		if (frm.is_new()) {
			frappe.contacts.clear_address_and_contact(frm);
		} else {
			frappe.contacts.render_address_and_contact(frm);
		}
	},
});
