// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Prospect', {
	refresh () {
		if (!cur_frm.is_new() && frappe.boot.user.can_create.includes("Customer")) {
			cur_frm.add_custom_button(__("Customer"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_customer",
					frm: cur_frm
				})
			}, __("Create"));
		}
		if (!cur_frm.is_new() && frappe.boot.user.can_create.includes("Opportunity")) {
			cur_frm.add_custom_button(__("Opportunity"), function() {
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.prospect.prospect.make_opportunity",
					frm: cur_frm
				})
			}, __("Create"));
		}
	},

	make_customer () {
		console.log("Make Customer");
		frappe.model.open_mapped_doc({
			method: "erpnext.crm.doctype.prospect.prospect.make_customer",
			frm: cur_frm
		})
	},

	make_opportunity () {
		console.log("Make Opportunity");
		// frappe.model.open_mapped_doc({
		// 	method: "erpnext.crm.doctype.lead.lead.make_opportunity",
		// 	frm: cur_frm
		// })
	}
});
