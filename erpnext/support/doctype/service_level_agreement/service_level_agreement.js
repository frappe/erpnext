// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Service Level Agreement', {
	setup: function(frm) {
		let allow_statuses = [];
		const exclude_statuses = ['Open', 'Closed', 'Resolved'];

		frappe.model.with_doctype('Issue', () => {
			let statuses = frappe.meta.get_docfield('Issue', 'status', frm.doc.name).options;
			statuses = statuses.split('\n');
			allow_statuses = statuses.filter((status) => !exclude_statuses.includes(status));
			frappe.meta.get_docfield('Pause SLA On Status', 'status', frm.doc.name).options = [''].concat(allow_statuses);
		});
	},
	onload: function(frm) {
		frm.set_query("document_type", function() {
			return {
				filters: [
					['DocType', 'issingle', '=', 0],
					['DocType', 'name', 'not in', frappe.model.core_doctypes_list],
					['DocType', 'module', 'not in', ["Email", "Core", "Custom", "Event Streaming", "Social", "Data Migration", "Geo", "Desk"]]
				]
			};
		});
	}
});