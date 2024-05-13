# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _

import erpnext


def get_level():
	activation_level = 0
	sales_data = []
	min_count = 0
	doctypes = {
		"Asset": 5,
		"BOM": 3,
		"Customer": 5,
		"Delivery Note": 5,
		"Employee": 3,
		"Issue": 5,
		"Item": 5,
		"Journal Entry": 3,
		"Lead": 3,
		"Material Request": 5,
		"Opportunity": 5,
		"Payment Entry": 2,
		"Project": 5,
		"Purchase Order": 2,
		"Purchase Invoice": 5,
		"Purchase Receipt": 5,
		"Quotation": 3,
		"Sales Order": 2,
		"Sales Invoice": 2,
		"Stock Entry": 3,
		"Supplier": 5,
		"Task": 5,
		"User": 5,
		"Work Order": 5,
	}

	for doctype, min_count in doctypes.items():
		count = frappe.db.count(doctype)
		if count > min_count:
			activation_level += 1
		sales_data.append({doctype: count})

	if frappe.db.get_single_value("System Settings", "setup_complete"):
		activation_level += 1

	communication_number = frappe.db.count("Communication", dict(communication_medium="Email"))
	if communication_number > 10:
		activation_level += 1
	sales_data.append({"Communication": communication_number})

	# recent login
	if frappe.db.sql("select name from tabUser where last_login > date_sub(now(), interval 2 day) limit 1"):
		activation_level += 1

	level = {"activation_level": activation_level, "sales_data": sales_data}

	return level


def get_help_messages():
	"""Returns help messages to be shown on Desktop"""
	if get_level() > 6:
		return []

	domain = frappe.get_cached_value("Company", erpnext.get_default_company(), "domain")
	messages = []

	message_settings = [
		frappe._dict(
			doctype="Lead",
			title=_("Create Leads"),
			description=_("Leads help you get business, add all your contacts and more as your leads"),
			action=_("Create Lead"),
			route="List/Lead",
			domain=("Manufacturing", "Retail", "Services", "Distribution"),
			target=3,
		),
		frappe._dict(
			doctype="Quotation",
			title=_("Create customer quotes"),
			description=_("Quotations are proposals, bids you have sent to your customers"),
			action=_("Create Quotation"),
			route="List/Quotation",
			domain=("Manufacturing", "Retail", "Services", "Distribution"),
			target=3,
		),
		frappe._dict(
			doctype="Sales Order",
			title=_("Manage your orders"),
			description=_("Create Sales Orders to help you plan your work and deliver on-time"),
			action=_("Create Sales Order"),
			route="List/Sales Order",
			domain=("Manufacturing", "Retail", "Services", "Distribution"),
			target=3,
		),
		frappe._dict(
			doctype="Purchase Order",
			title=_("Create Purchase Orders"),
			description=_("Purchase orders help you plan and follow up on your purchases"),
			action=_("Create Purchase Order"),
			route="List/Purchase Order",
			domain=("Manufacturing", "Retail", "Services", "Distribution"),
			target=3,
		),
		frappe._dict(
			doctype="User",
			title=_("Create Users"),
			description=_(
				"Add the rest of your organization as your users. You can also add invite Customers to your portal by adding them from Contacts"
			),
			action=_("Create User"),
			route="List/User",
			domain=("Manufacturing", "Retail", "Services", "Distribution"),
			target=3,
		),
		frappe._dict(
			doctype="Timesheet",
			title=_("Add Timesheets"),
			description=_(
				"Timesheets help keep track of time, cost and billing for activities done by your team"
			),
			action=_("Create Timesheet"),
			route="List/Timesheet",
			domain=("Services",),
			target=5,
		),
		frappe._dict(
			doctype="Employee",
			title=_("Create Employee Records"),
			description=_("Create Employee records."),
			action=_("Create Employee"),
			route="List/Employee",
			target=3,
		),
	]

	for m in message_settings:
		if not m.domain or domain in m.domain:
			m.count = frappe.db.count(m.doctype)
			if m.count < m.target:
				messages.append(m)

	return messages
