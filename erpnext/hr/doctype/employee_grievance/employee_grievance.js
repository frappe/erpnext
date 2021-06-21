// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Grievance', {
	setup: function(frm) {
		frm.set_query('grievance_against_party', function() {
			return {
				filters: {
					name: ['in', [
						'Company', 'Department', 'Employee Group', 'Employee Grade', 'Employee']
					]
				}
			};
		});
		frm.set_query('associated_document_type', function() {
			let ignore_modules = ["Setup", "Core", "Integrations", "Automation", "Website",
				"Utilities", "Event Streaming", "Social", "Chat", "Data Migration", "Printing", "Desk", "Custom"];
			return {
				filters: {
					istable: 0,
					issingle: 0,
					module: ["Not In", ignore_modules]
				}
			};
		});
	},

	grievance_against_party: function(frm) {
		let filters = {};
		if (frm.doc.grievance_against_party == 'Employee' && frm.doc.raised_by) {
			filters.name =  ["!=", frm.doc.raised_by];
		}
		frm.set_query('grievance_against', function() {
			return {
				filters: filters
			};
		});
	},
});
