// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("contract_template", "contract_terms", "contract_terms");
cur_frm.add_fetch("contract_template", "requires_fulfilment", "requires_fulfilment");

// Add fulfilment terms from contract template into contract
frappe.ui.form.on("Contract", {
	contract_template: function (frm) {
		// Populate the fulfilment terms table from a contract template, if any
		if (frm.doc.contract_template) {
			frappe.model.with_doc("Contract Template", frm.doc.contract_template, function () {
				let tabletransfer = frappe.model.get_doc("Contract Template", frm.doc.contract_template);

				// populate contract sections table
				frm.doc.contract_sections = [];
				$.each(tabletransfer.contract_sections, function (index, row) {
					let d = frm.add_child("contract_sections");
					d.section = row.section;
					d.description = row.description;
					frm.refresh_field("contract_sections");
				});

				// populate fulfilment terms table
				frm.doc.fulfilment_terms = [];
				$.each(tabletransfer.fulfilment_terms, function (index, row) {
					let d = frm.add_child("fulfilment_terms");
					d.requirement = row.requirement;
					frm.refresh_field("fulfilment_terms");
				});
			});
		}
	}
});
