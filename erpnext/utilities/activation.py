import frappe

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

	if frappe.db.count('Payment Entry') > 2:
		activation_level += 1

	if frappe.db.count('Communication', dict(communication_medium='Email')) > 10:
		activation_level += 1

	if frappe.db.count('User') > 5:
		activation_level += 1

	# recent login
	if frappe.db.sql('select name from tabUser where last_login > date_sub(now(), interval 2 day) limit 1'):
		activation_level += 1

	return activation_level