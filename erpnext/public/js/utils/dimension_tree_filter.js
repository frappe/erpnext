frappe.provide('frappe.ui.form');

erpnext.doctypes_with_dimensions = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Asset",
	"Expense Claim", "Stock Entry", "Budget", "Payroll Entry", "Delivery Note", "Shipping Rule", "Loyalty Program",
	"Fee Schedule", "Fee Structure", "Stock Reconciliation", "Travel Request", "Fees", "POS Profile", "Opening Invoice Creation Tool",
	"Subscription", "Purchase Order", "Journal Entry", "Material Request", "Purchase Receipt", "Landed Cost Item", "Asset"];

erpnext.child_docs = ["Sales Invoice Item", "Purchase Invoice Item", "Purchase Order Item", "Journal Entry Account",
	"Material Request Item", "Delivery Note Item", "Purchase Receipt Item", "Stock Entry Detail", "Payment Entry Deduction",
	"Landed Cost Item", "Asset Value Adjustment", "Opening Invoice Creation Tool Item", "Subscription Plan"];

frappe.call({
	method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimension_filters",
	callback: function(r){
		erpnext.dimension_filters = r.message[0];
		erpnext.default_dimensions = r.message[1];
	}
});

erpnext.doctypes_with_dimensions.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		onload: function(frm) {
			erpnext.dimension_filters.forEach((dimension) => {
				frappe.model.with_doctype(dimension['document_type'], () => {
					if (frappe.meta.has_field(dimension['document_type'], 'is_group')) {
						frm.set_query(dimension['fieldname'], {
							"is_group": 0
						});
					}

					if (Object.keys(erpnext.default_dimensions).length > 0) {
						if (frappe.meta.has_field(doctype, dimension['fieldname'])) {
							if (frm.is_new() && frappe.meta.has_field(doctype, 'company') && frm.doc.company) {
								frm.set_value(dimension['fieldname'], erpnext.default_dimensions[frm.doc.company][dimension['document_type']]);
							}
						}

						if (frm.doc.items && frm.doc.items.length && frm.doc.docstatus === 0
							&& (!frm.doc.items[0][dimension['fieldname']])) {
							frm.doc.items[0][dimension['fieldname']] = erpnext.default_dimensions[frm.doc.company][dimension['document_type']];
						}

						if (frm.doc.accounts && frm.doc.accounts.length && frm.doc.docstatus === 0
							&& (!frm.doc.items[0][dimension['fieldname']])) {
							frm.doc.accounts[0][dimension['fieldname']] = erpnext.default_dimensions[frm.doc.company][dimension['document_type']];
						}
					}
				});
			});
		},

		company: function(frm) {
			if(frm.doc.company && (Object.keys(erpnext.default_dimensions).length > 0)) {
				erpnext.dimension_filters.forEach((dimension) => {
					if (frappe.meta.has_field(doctype, dimension['fieldname'])) {
						frm.set_value(dimension['fieldname'], erpnext.default_dimensions[frm.doc.company][dimension['document_type']]);
					}
				});
			}
		},
	});
});

erpnext.child_docs.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		items_add: function(frm, cdt, cdn) {
			erpnext.dimension_filters.forEach((dimension) => {
				var row = frappe.get_doc(cdt, cdn);
				frm.script_manager.copy_from_first_row("items", row, [dimension['fieldname']]);
			});
		},

		accounts_add: function(frm, cdt, cdn) {
			erpnext.dimension_filters.forEach((dimension) => {
				var row = frappe.get_doc(cdt, cdn);
				frm.script_manager.copy_from_first_row("accounts", row, [dimension['fieldname']]);
			});
		},

		company: function(frm) {
			if(frm.doc.company) {
				erpnext.dimension_filters.forEach((dimension) => {
					frm.set_value(dimension['fieldname'], erpnext.default_dimensions[frm.doc.company][dimension['document_type']]);
				});
			}
		},

		items_add: function(frm, cdt, cdn) {
			erpnext.dimension_filters.forEach((dimension) => {
				var row = frappe.get_doc(cdt, cdn);
				frm.script_manager.copy_from_first_row("items", row, [dimension['fieldname']]);
			});
		},

		accounts_add: function(frm, cdt, cdn) {
			erpnext.dimension_filters.forEach((dimension) => {
				var row = frappe.get_doc(cdt, cdn);
				frm.script_manager.copy_from_first_row("accounts", row, [dimension['fieldname']]);
			});
		}
	});
});