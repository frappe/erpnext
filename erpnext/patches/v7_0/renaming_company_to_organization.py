import frappe

from frappe.model.utils.rename_field import rename_field
from frappe.modules import scrub, get_doctype_module

def execute():
	frappe.rename_doc("DocType", "Company", "organization", force=True)
	frappe.rename_doc("DocType", "Fiscal Year Company", "Fiscal Year Organization", force=True)
	
	doctypes = [
		"Account", "C-Form" , "Cost Center", "Fiscal Year Organization", "GL Entry", 
		"Journal Entry", "Mode of Payment Account", 
		"Party Account", "Period Closing Voucher", "POS Profile", "Pricing Rule", 
		"Purchase Invoice", "Purchase Taxes and Charges Template", 
		"Sales Invoice", "Sales Taxes and Charges Template", "Shipping Rule", "Tax Rule", 
		"Purchase Order", "Supplier Quotation", "Lead", "Opportunity", "Appraisal", "Attendance",
		"Employee", "Expense Claim", "Leave Application", "Leave Block List", "Offer Letter",
		"Salary Slip", "Salary Structure", "BOM", "Production Order", "Sales Order", "Project", 
		"Task", "Warranty Claim", "Maintenance Visit", "Installation Note", "Quotation",
		"Authorization Rule", "Email Digest", "Shopping Cart Settings", "Delivery Note", 
		"Landed Cost Voucher", "Material Request", "Purchase Receipt", "Serial No", 
		"Stock Entry", "Stock Ledger Entry", "Stock Reconciliation", "Warehouse", 
		"Issue", "Maintenance Schedule"
	] 

	for dt in doctypes:
		frappe.reload_doc(get_doctype_module(dt), "doctype", scrub(dt), force=True)
		rename_field(dt, "company", "organization")
	
	reload_doctypes = ["Employee External Work History", "Global Defaults", "Organization", "Fiscal Year"]
	for dt in reload_doctypes:
		frappe.reload_doc(get_doctype_module(dt), "doctype", scrub(dt), force=True)
	
	rename_field("Organization", "company_name", "organization_name")
	rename_field("Global Defaults", "default_company", "default_organization")	
	rename_field("Fiscal Year", "companies", "organizations")	
	rename_field("Lead", "company_name", "organization_name")
	rename_field("Employee", "company_email", "organization_email")	
	rename_field("Employee", "history_in_company", "history_in_organization")	
	rename_field("Employee External Work History", "company_name", "organization")	
	rename_field("Warranty Claim", "from_company", "from_organization")	