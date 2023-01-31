// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prospect', {
	refresh (frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: frm.doctype };

		if (!frm.is_new() && frappe.boot.user.can_create.includes("Customer")) {
			frm.add_custom_button(__("Customer"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_customer",
					frm: frm
				});
			}, __("Create"));
		}
		if (!frm.is_new() && frappe.boot.user.can_create.includes("Opportunity")) {
			frm.add_custom_button(__("Opportunity"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
					frm: frm
				});
			}, __("Create"));
		}

		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
		frm.trigger("show_notes");
		frm.trigger("show_activities");
	},

	show_notes (frm) {
		const crm_notes = new erpnext.utils.CRMNotes({
			frm: frm,
			notes_wrapper: $(frm.fields_dict.notes_html.wrapper),
		});
		crm_notes.refresh();
	},

	show_activities (frm) {
		const crm_activities = new erpnext.utils.CRMActivities({
			frm: frm,
			open_activities_wrapper: $(frm.fields_dict.open_activities_html.wrapper),
			all_activities_wrapper: $(frm.fields_dict.all_activities_html.wrapper),
			form_wrapper: $(frm.wrapper),
		});
		crm_activities.refresh();
	}

});
