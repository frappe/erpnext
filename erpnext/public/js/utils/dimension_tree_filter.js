frappe.provide('frappe.ui.form');

erpnext.doctypes_with_dimensions = ["GL Entry", "Sales Invoice", "Purchase Invoice", "Payment Entry", "Asset",
	"Expense Claim", "Stock Entry", "Budget", "Payroll Entry", "Delivery Note", "Sales Invoice Item", "Purchase Invoice Item",
	"Purchase Order Item", "Journal Entry Account", "Material Request Item", "Delivery Note Item", "Purchase Receipt Item",
	"Stock Entry Detail", "Payment Entry Deduction", "Sales Taxes and Charges", "Purchase Taxes and Charges", "Shipping Rule",
	"Landed Cost Item", "Asset Value Adjustment", "Loyalty Program", "Fee Schedule", "Fee Structure", "Stock Reconciliation",
	"Travel Request", "Fees", "POS Profile"];

let dimension_filters = erpnext.get_dimension_filters();

erpnext.doctypes_with_dimensions.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		onload: function(frm) {
			dimension_filters.then((dimensions) => {
				dimensions.forEach((dimension) => {
					frm.set_query(dimension['fieldname'],{
						"is_group": 0
					});
				});
			});
		}
	});
});