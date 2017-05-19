import frappe, erpnext

from frappe import _

def get_level():
	activation_level = 0
	if frappe.db.get_single_value('System Settings', 'setup_complete'):
		activation_level = 1

	if frappe.db.count('Item') > 5:
		activation_level += 1

	if frappe.db.count('Customer') > 5:
		activation_level += 1

	if frappe.db.count('Sales Order') > 2:
		activation_level += 1

	if frappe.db.count('Purchase Order') > 2:
		activation_level += 1

	if frappe.db.count('Employee') > 3:
		activation_level += 1

	if frappe.db.count('Lead') > 3:
		activation_level += 1

	if frappe.db.count('Payment Entry') > 2:
		activation_level += 1

	if frappe.db.count('Communication', dict(communication_medium='Email')) > 10:
		activation_level += 1

	if frappe.db.count('User') > 5:
		activation_level += 1

	if frappe.db.count('Student') > 5:
		activation_level += 1

	if frappe.db.count('Instructor') > 5:
		activation_level += 1

	# recent login
	if frappe.db.sql('select name from tabUser where last_login > date_sub(now(), interval 2 day) limit 1'):
		activation_level += 1

	return activation_level

def get_help_messages():
	'''Returns help messages to be shown on Desktop'''
	if get_level() > 6:
		return []

	messages = []

	domain = frappe.db.get_value('Company', erpnext.get_default_company(), 'domain')

	message_settings = [
		frappe._dict(
			doctype='Lead',
			title=_('Create Leads'),
			description=_('Leads help you get business, add all your contacts and more as your leads'),
			action=_('Make Lead'),
			route='List/Lead',
			domain=('Manufacturing', 'Retail', 'Services', 'Distribution'),
			target=3
		),
		frappe._dict(
			doctype='Quotation',
			title=_('Create customer quotes'),
			description=_('Quotations are proposals, bids you have sent to your customers'),
			action=_('Make Quotation'),
			route='List/Quotation',
			domain=('Manufacturing', 'Retail', 'Services', 'Distribution'),
			target=3
		),
		frappe._dict(
			doctype='Sales Order',
			title=_('Manage your orders'),
			description=_('Make Sales Orders to help you plan your work and deliver on-time'),
			action=_('Make Sales Order'),
			route='List/Sales Order',
			domain=('Manufacturing', 'Retail', 'Services', 'Distribution'),
			target=3
		),
		frappe._dict(
			doctype='Purchase Order',
			title=_('Create Purchase Orders'),
			description=_('Purchase orders help you plan and follow up on your purchases'),
			action=_('Make Purchase Order'),
			route='List/Purchase Order',
			domain=('Manufacturing', 'Retail', 'Services', 'Distribution'),
			target=3
		),
		frappe._dict(
			doctype='User',
			title=_('Create Users'),
			description=_('Add the rest of your organization as your users. You can also add invite Customers to your portal by adding them from Contacts'),
			action=_('Make User'),
			route='List/User',
			domain=('Manufacturing', 'Retail', 'Services', 'Distribution'),
			target=3
		),
		frappe._dict(
			doctype='Timesheet',
			title=_('Add Timesheets'),
			description=_('Timesheets help keep track of time, cost and billing for activites done by your team'),
			action=_('Make Timesheet'),
			route='List/Timesheet',
			domain=('Services',),
			target=5
		),
		frappe._dict(
			doctype='Student',
			title=_('Add Students'),
			description=_('Students are at the heart of the system, add all your students'),
			action=_('Make Student'),
			route='List/Student',
			domain=('Education',),
			target=5
		),
		frappe._dict(
			doctype='Student Batch',
			title=_('Group your students in batches'),
			description=_('Student Batches help you track attendance, assessments and fees for students'),
			action=_('Make Student Batch'),
			route='List/Student Batch',
			domain=('Education',),
			target=3
		),
		frappe._dict(
			doctype='Employee',
			title=_('Create Employee Records'),
			description=_('Create Employee records to manage leaves, expense claims and payroll'),
			action=_('Make Employee'),
			route='List/Employee',
			target=3
		)
	]


	for m in message_settings:
		if not m.domain or domain in m.domain:
			m.count = frappe.db.count(m.doctype)
			if m.count < m.target:
				messages.append(m)

	return messages
