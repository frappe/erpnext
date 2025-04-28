import frappe


def execute():
	frappe.reload_doctype("Quotation")
	# update customer_name from Customer document if quotation_to is set to Customer
	frappe.db.sql(
		"""
		update tabQuotation, tabCustomer
		set
			tabQuotation.customer_name = tabCustomer.customer_name,
<<<<<<< HEAD
=======
			tabQuotation.title = tabCustomer.customer_name
>>>>>>> 7c4cf3e834 (Favicon.svg)
		where
			tabQuotation.customer_name is null
			and tabQuotation.party_name = tabCustomer.name
			and tabQuotation.quotation_to = 'Customer'
	"""
	)

	# update customer_name from Lead document if quotation_to is set to Lead

	frappe.db.sql(
		"""
		update tabQuotation, tabLead
		set
			tabQuotation.customer_name =  case when ifnull(tabLead.company_name, '') != '' then tabLead.company_name else tabLead.lead_name end,
<<<<<<< HEAD
=======
			tabQuotation.title = case when ifnull(tabLead.company_name, '') != '' then tabLead.company_name else tabLead.lead_name end
>>>>>>> 7c4cf3e834 (Favicon.svg)
		where
			tabQuotation.customer_name is null
			and tabQuotation.party_name = tabLead.name
			and tabQuotation.quotation_to = 'Lead'
	"""
	)
