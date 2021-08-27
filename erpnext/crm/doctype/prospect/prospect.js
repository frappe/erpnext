// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prospect', {
	refresh (frm) {
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
	}
});
