// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prospect', {
	refresh () {
		if (!cur_frm.is_new() && frappe.boot.user.can_create.includes("Customer")) {
			cur_frm.add_custom_button(__("Customer"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_customer",
					frm: cur_frm
				});
			}, __("Create"));
		}
		if (!cur_frm.is_new() && frappe.boot.user.can_create.includes("Opportunity")) {
			cur_frm.add_custom_button(__("Opportunity"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
					frm: cur_frm
				});
			}, __("Create"));
		}

		if (!cur_frm.is_new()) {
			frappe.contacts.render_address_and_contact(cur_frm);
			cur_frm.trigger('render_contact_day_html');
		} else {
			frappe.contacts.clear_address_and_contact(cur_frm);
		}
	}
});
