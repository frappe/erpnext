import webnotes

def execute():
	"""
		* Reload email_digest doctype
		* Create default email digest
	"""
	from webnotes.modules.module_manager import reload_doc
	
	# Minor fix in print_format doctype
	#reload_doc('core', 'doctype', 'print_format')
	
	#reload_doc('setup', 'doctype', 'email_digest')

	#global create_default_email_digest
	#create_default_email_digest()

	global enabled_default_email_digest
	enabled_default_email_digest()


def enabled_default_email_digest():
	"""
		Enables the created email digest
	"""
	from webnotes.model.doc import Document
	from webnotes.model.code import get_obj
	companies_list = webnotes.conn.sql("SELECT company_name FROM `tabCompany`", as_list=1)
	for company in companies_list:
		if company and company[0]:
			edigest = Document('Email Digest', 'Default Weekly Digest - ' + company[0])
			if edigest:
				edigest.enabled = 1
				edigest.save()
				ed_obj = get_obj(doc=edigest)
				ed_obj.on_update()



def create_default_email_digest():
	"""
		* Weekly Digest
		* For all companies
		* Recipients: System Managers
		* Full content
		* Disabled by default
	"""
	from webnotes.model.doc import Document
	companies_list = webnotes.conn.sql("SELECT company_name FROM `tabCompany`", as_list=1)
	global get_system_managers
	system_managers = get_system_managers()
	for company in companies_list:
		if company and company[0]:
			edigest = Document('Email Digest')
			edigest.name = "Default Weekly Digest - " + company[0]
			edigest.company = company[0]
			edigest.frequency = 'Weekly'
			edigest.recipient_list = system_managers
			edigest.new_leads = 1
			edigest.new_enquiries = 1
			edigest.new_quotations = 1
			edigest.new_sales_orders = 1
			edigest.new_purchase_orders = 1
			edigest.new_transactions = 1
			edigest.payables = 1
			edigest.payments = 1
			edigest.expenses_booked = 1
			edigest.invoiced_amount = 1
			edigest.collections = 1
			edigest.income = 1
			edigest.bank_balance = 1
			exists = webnotes.conn.sql("""\
				SELECT name FROM `tabEmail Digest`
				WHERE name = %s""", edigest.name)
			if (exists and exists[0]) and exists[0][0]:
				continue
			else:
				edigest.save(1)


def get_system_managers():
	"""
		Returns a string of system managers' email addresses separated by \n
	"""
	system_managers_list = webnotes.conn.sql("""\
		SELECT DISTINCT p.name
		FROM tabUserRole ur, tabProfile p
		WHERE
			ur.parent = p.name AND
			ur.role='System Manager' AND
			p.docstatus<2 AND
			p.enabled=1 AND
			p.name not in ('Administrator', 'Guest')""", as_list=1)

	return "\n".join([sysman[0] for sysman in system_managers_list])

