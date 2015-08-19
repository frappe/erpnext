# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.db.sql("""update `tabAccount` acc 
		set currency = (select default_currency from tabCompany where name=acc.company)
		where ifnull(currency, '') = ''""")