frappe.provide('frappe.ui.form');

erpnext.doctypes_with_dimensions = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Asset",
	"Expense Claim", "Stock Entry", "Budget", "Payroll Entry", "Delivery Note", "Sales Invoice Item", "Purchase Invoice Item",
	"Purchase Order Item", "Journal Entry Account", "Material Request Item", "Delivery Note Item", "Purchase Receipt Item",
	"Stock Entry Detail", "Payment Entry Deduction", "Sales Taxes and Charges", "Purchase Taxes and Charges", "Shipping Rule",
	"Landed Cost Item", "Asset Value Adjustment", "Loyalty Program", "Fee Schedule", "Fee Structure", "Stock Reconciliation",
	"Travel Request", "Fees", "POS Profile", "Opening Invoice Creation Tool", "Opening Invoice Creation Tool Item", "Subscription",
	"Subscription Plan"];

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
					if (frm.is_new() && frappe.meta.has_field(doctype, 'company') && frm.doc.company) {
						frm.set_value(dimension['fieldname'], erpnext.default_dimensions[frm.doc.company][dimension['document_type']]);
					}
				});
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