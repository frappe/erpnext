# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import erpnext

def execute():
	"""Create domain documents"""
	frappe.reload_doctype("Domain")

	for domain in ("Distribution", "Manufacturing", "Retail", "Services", "Education"):
		if not frappe.db.exists({'doctype': 'Domain', 'domain': domain}):
			doc = frappe.new_doc("Domain")
			doc.domain = domain
			doc.save()


	# set domain in domain settings based on company domain

	domains = []
	condition = ""
	company = erpnext.get_default_company()
	if company:
		condition = " and name='{0}'".format(company)

	domains = frappe.db.sql_list("select distinct domain from `tabCompany` where domain != 'Other' {0}".format(condition))

	if not domains:
		return

	domain_settings = frappe.get_doc("Domain Settings", "Domain Settings")
	checked_domains = [row.domain for row in domain_settings.active_domains]

	for domain in domains:
		# check and ignore if the domains is already checked in domain settings
		if domain in checked_domains:
			continue

		row = domain_settings.append("active_domains", dict(domain=domain))

	domain_settings.save(ignore_permissions=True)