# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import frappe
from collections import Counter
from frappe.core.doctype.user.user import STANDARD_USERS

def execute():
	system_settings = frappe.get_doc("System Settings")

	# set values from global_defauls
	global_defauls = frappe.db.get_value("Global Defaults", None,
		["time_zone", "date_format", "number_format", "float_precision", "session_expiry"])

	if global_defauls:
		for key, val in global_defauls.items():
			if not system_settings.get(key):
				system_settings[key] = val

	# language
	if not system_settings.get("language"):
		# find most common language
		lang = frappe.db.sql_list("""select language from `tabUser`
			where ifnull(language, '')!='' and language not like "Loading%%" and name not in ({standard_users})""".format(
			standard_users=", ".join(["%s"]*len(STANDARD_USERS))), tuple(STANDARD_USERS))
		lang = Counter(lang).most_common(1)
		lang = (len(lang) > 0) and lang[0][0] or "english"

		system_settings.language = lang

	system_settings.save()
