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
	}
});