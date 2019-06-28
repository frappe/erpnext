import frappe

def execute():
	frappe.reload_doctype("Quotation")
	# update customer_name from Customer document if quotation_to is set to Customer
	frappe.db.sql('''
		update tabQuotation, tabCustomer
		set
			tabQuotation.customer_name = tabCustomer.customer_name,
			tabQuotation.title = tabCustomer.customer_name
		where
			tabQuotation.customer_name is null
			and tabQuotation.party_name = tabCustomer.name
			and tabQuotation.quotation_to = 'Customer'
	''')

	# update customer_name from Lead document if quotation_to is set to Lead

	frappe.db.sql('''
		update tabQuotation, tabLead
		set
			tabQuotation.customer_name =  case when ifnull(tabLead.company_name, '') != '' then tabLead.company_name else tabLead.lead_name end,
			tabQuotation.title = case when ifnull(tabLead.company_name, '') != '' then tabLead.company_name else tabLead.lead_name end
		where
			tabQuotation.customer_name is null
			and tabQuotation.party_name = tabLead.name
			and tabQuotation.quotation_to = 'Lead'
	''')
