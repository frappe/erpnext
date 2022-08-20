import frappe


def is_official_voucher(gl_entries):
	company = None
	if gl_entries:
		company = gl_entries[0].company

	official_accounts = []
	if company:
		official_accounts = get_official_accounts_from_company(company)

	for d in gl_entries:
		account_type =  frappe.get_cached_value('Account', d.account, 'account_type')
		if account_type in ['Bank', 'Tax']:
			return True
		if d.account in official_accounts:
			return True

	return False


def get_official_accounts_from_company(company):
	doc = frappe.get_cached_doc('Company', company)
	
	official_accounts = []
	if doc.sales_tax_account:
		official_accounts.append(doc.sales_tax_account)
	if doc.service_tax_account:
		official_accounts.append(doc.service_tax_account)
	if doc.further_tax_account:
		official_accounts.append(doc.further_tax_account)
	if doc.extra_tax_account:
		official_accounts.append(doc.extra_tax_account)
	if doc.advance_tax_account:
		official_accounts.append(doc.advance_tax_account)
	
	return official_accounts
