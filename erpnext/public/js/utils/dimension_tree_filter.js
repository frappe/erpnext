frappe.provide('frappe.ui.form');

let default_dimensions = {};

let doctypes_with_dimensions = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Asset",
	"Expense Claim", "Stock Entry", "Budget", "Payroll Entry", "Delivery Note", "Shipping Rule", "Loyalty Program",
	"Fee Schedule", "Fee Structure", "Stock Reconciliation", "Travel Request", "Fees", "POS Profile", "Opening Invoice Creation Tool",
	"Subscription", "Purchase Order", "Journal Entry", "Material Request", "Purchase Receipt", "Landed Cost Item", "Asset"];

let child_docs = ["Sales Invoice Item", "Purchase Invoice Item", "Purchase Order Item", "Journal Entry Account",
	"Material Request Item", "Delivery Note Item", "Purchase Receipt Item", "Stock Entry Detail", "Payment Entry Deduction",
	"Landed Cost Item", "Asset Value Adjustment", "Opening Invoice Creation Tool Item", "Subscription Plan"];

frappe.call({
	method: "erpnext.accounts.doctype.accounting_dimension.accounting_dimension.get_dimension_filters",
	callback: function(r) {
		erpnext.dimension_filters = r.message[0];
		default_dimensions = r.message[1];
	}
});

doctypes_with_dimensions.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		onload: function(frm) {
			erpnext.dimension_filters.forEach((dimension) => {
				frappe.model.with_doctype(dimension['document_type'], () => {
					if(frappe.meta.has_field(dimension['document_type'], 'is_group')) {
						frm.set_query(dimension['fieldname'], {
							"is_group": 0
						});
					}
				});
			});
		},

		company: function(frm) {
			if(frm.doc.company && (Object.keys(default_dimensions || {}).length > 0)
				&& default_dimensions[frm.doc.company]) {
				frm.trigger('update_dimension');
			}
		},

		update_dimension: function(frm) {
			erpnext.dimension_filters.forEach((dimension) => {
				if(frm.is_new()) {
					if(frm.doc.company && Object.keys(default_dimensions || {}).length > 0
						&& default_dimensions[frm.doc.company]) {

						let default_dimension = default_dimensions[frm.doc.company][dimension['fieldname']];

						if(default_dimension) {
							if (frappe.meta.has_field(doctype, dimension['fieldname'])) {
								frm.set_value(dimension['fieldname'], default_dimension);
							}

							$.each(frm.doc.items || frm.doc.accounts || [], function(i, row) {
								frappe.model.set_value(row.doctype, row.name, dimension['fieldname'], default_dimension);
							});
						}
					}
				}
			});
		}
	});
});

child_docs.forEach((doctype) => {
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
		}
	});
});