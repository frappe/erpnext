// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Blanket Order', {
	refresh: function(frm) {
		if (frm.doc.customer) {
			frm.add_custom_button(__('View Orders'), function() {
				frappe.set_route('List', 'Sales Order', {blanket_order: frm.doc.name});
			});
			if (frm.doc.docstatus === 1) {
				frm.add_primary_button(__("Create Sales Order"), function(){
					
				});
			}
		}

		if (frm.doc.supplier) {
			frm.add_custom_button(__('View Orders'), function() {
				frappe.set_route('List', 'Purchase Order', {blanket_order: frm.doc.name});
			});
		}

		// if (frm.doc.project) {
		// 	frm.add_custom_button(__('Project'), function() {
		// 		frappe.set_route("Form", "Project", frm.doc.project);
		// 	},__("View"));
		// 	frm.add_custom_button(__('Task'), function() {
		// 		frappe.set_route('List', 'Task', {project: frm.doc.project});
		// 	},__("View"));
		// }

		if ((!frm.doc.employee) && (frm.doc.docstatus === 1)) {
			frm.add_custom_button(__('Employee'), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.hr.doctype.employee_onboarding.employee_onboarding.make_employee",
					frm: frm
				});
			}, __("Make"));
			frm.page.set_inner_btn_group_as_primary(__("Make"));
		}

	}
});
