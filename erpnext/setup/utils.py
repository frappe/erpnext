# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils import get_datetime_str, nowdate

def get_root_of(doctype):
	"""Get root element of a DocType with a tree structure"""
	result = frappe.db.sql_list("""select name from `tab%s`
		where lft=1 and rgt=(select max(rgt) from `tab%s` where docstatus < 2)""" %
		(doctype, doctype))
	return result[0] if result else None

def get_ancestors_of(doctype, name):
	"""Get ancestor elements of a DocType with a tree structure"""
	lft, rgt = frappe.db.get_value(doctype, name, ["lft", "rgt"])
	result = frappe.db.sql_list("""select name from `tab%s`
		where lft<%s and rgt>%s order by lft desc""" % (doctype, "%s", "%s"), (lft, rgt))
	return result or []

def before_tests():
	frappe.clear_cache()
	# complete setup if missing
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
	if not frappe.get_list("Company"):
		setup_complete({
			"currency"			:"USD",
			"full_name"			:"Test User",
			"company_name"		:"Wind Power LLC",
			"timezone"			:"America/New_York",
			"company_abbr"		:"WP",
			"industry"			:"Manufacturing",
			"country"			:"United States",
			"fy_start_date"		:"2011-01-01",
			"fy_end_date"		:"2011-12-31",
			"language"			:"english",
			"company_tagline"	:"Testing",
			"email"				:"test@erpnext.com",
			"password"			:"test",
			"chart_of_accounts" : "Standard",
			"domain"			: "Manufacturing"
		})

	frappe.db.sql("delete from `tabLeave Allocation`")
	frappe.db.sql("delete from `tabLeave Application`")
	frappe.db.sql("delete from `tabSalary Slip`")
	frappe.db.sql("delete from `tabItem Price`")

	frappe.db.set_value("Stock Settings", None, "auto_insert_price_list_rate_if_missing", 0)
	enable_all_roles_and_domains()

	frappe.db.commit()

@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, transaction_date=None):
	if not transaction_date:
		transaction_date = nowdate()
	if not (from_currency and to_currency):
		# manqala 19/09/2016: Should this be an empty return or should it throw and exception?
		return

	if from_currency == to_currency:
		return 1

	# cksgb 19/09/2016: get last entry in Currency Exchange with from_currency and to_currency.
	entries = frappe.get_all("Currency Exchange", fields = ["exchange_rate"],
		filters=[
			["date", "<=", get_datetime_str(transaction_date)],
			["from_currency", "=", from_currency],
			["to_currency", "=", to_currency]
		], order_by="date desc", limit=1)

	if entries:
		return flt(entries[0].exchange_rate)

	try:
		cache = frappe.cache()
		key = "currency_exchange_rate:{0}:{1}".format(from_currency, to_currency)
		value = cache.get(key)

		if not value:
			import requests
			response = requests.get("http://api.fixer.io/latest", params={
				"base": from_currency,
				"symbols": to_currency
			})
			# expire in 6 hours
			response.raise_for_status()
			value = response.json()["rates"][to_currency]
			cache.setex(key, value, 6 * 60 * 60)
		return flt(value)
	except:
		frappe.msgprint(_("Unable to find exchange rate for {0} to {1} for key date {2}. Please create a Currency Exchange record manually").format(from_currency, to_currency, transaction_date))
		return 0.0

def enable_all_roles_and_domains():
	""" enable all roles and domain for testing """
	roles = frappe.get_list("Role", filters={"disabled": 1})
	for role in roles:
		_role = frappe.get_doc("Role", role.get("name"))
		_role.disabled = 0
		_role.flags.ignore_mandatory = True
		_role.flags.ignore_permissions = True
		_role.save()

	# add all roles to users
	user = frappe.get_doc("User", "test@erpnext.com")
	user.add_roles(*[role.get("name") for role in roles])

	domains = frappe.get_list("Domain")
	if not domains:
		return

	domain_settings = frappe.get_doc("Domain Settings", "Domain Settings")
	domain_settings.set("active_domains", [])
	for domain in domains:
		row = domain_settings.append("active_domains", {})
		row.domain=domain.get("name")

	domain_settings.save()
