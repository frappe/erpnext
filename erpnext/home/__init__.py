# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import frappe
from frappe import msgprint

feed_dict = {
	# Project
	'Project': ['[%(status)s]', '#000080'],
	'Task': ['[%(status)s] %(subject)s', '#000080'],

	# Sales
	'Lead': ['%(lead_name)s', '#000080'],
	'Quotation': ['[%(status)s] To %(customer_name)s worth %(currency)s %(grand_total_export)s', '#4169E1'],
	'Sales Order': ['[%(status)s] To %(customer_name)s worth %(currency)s %(grand_total_export)s', '#4169E1'],

	# Purchase
	'Supplier': ['%(supplier_name)s, %(supplier_type)s', '#6495ED'],
	'Purchase Order': ['[%(status)s] %(name)s To %(supplier_name)s for %(currency)s  %(grand_total_import)s', '#4169E1'],

	# Stock
	'Delivery Note': ['[%(status)s] To %(customer_name)s', '#4169E1'],
	'Purchase Receipt': ['[%(status)s] From %(supplier)s', '#4169E1'],

	# Accounts
	'Journal Voucher': ['[%(voucher_type)s] %(name)s', '#4169E1'],
	'Purchase Invoice': ['To %(supplier_name)s for %(currency)s %(grand_total_import)s', '#4169E1'],
	'Sales Invoice': ['To %(customer_name)s for %(currency)s %(grand_total_export)s', '#4169E1'],

	# HR
	'Expense Claim': ['[%(approval_status)s] %(name)s by %(employee_name)s', '#4169E1'],
	'Salary Slip': ['%(employee_name)s for %(month)s %(fiscal_year)s', '#4169E1'],
	'Leave Transaction': ['%(leave_type)s for %(employee)s', '#4169E1'],

	# Support
	'Customer Issue': ['[%(status)s] %(description)s by %(customer_name)s', '#000080'],
	'Maintenance Visit': ['To %(customer_name)s', '#4169E1'],
	'Support Ticket': ["[%(status)s] %(subject)s", '#000080'],

	# Website
	'Web Page': ['%(title)s', '#000080'],
	'Blog': ['%(title)s', '#000080']
}

def make_feed(feedtype, doctype, name, owner, subject, color):
	"makes a new Feed record"
	#msgprint(subject)
	from frappe.utils import get_fullname

	if feedtype in ('Login', 'Comment', 'Assignment'):
		# delete old login, comment feed
		frappe.db.sql("""delete from tabFeed where
			datediff(curdate(), creation) > 7 and doc_type in ('Comment', 'Login', 'Assignment')""")
	else:
		# one feed per item
		frappe.db.sql("""delete from tabFeed
			where doc_type=%s and doc_name=%s
			and ifnull(feed_type,'') != 'Comment'""", (doctype, name))

	f = frappe.new_doc('Feed')
	f.owner = owner
	f.feed_type = feedtype
	f.doc_type = doctype
	f.doc_name = name
	f.subject = subject
	f.color = color
	f.full_name = get_fullname(owner)
	f.save(ignore_permissions=True)

def update_feed(doc, method=None):
	"adds a new feed"
	if frappe.flags.in_patch:
		return

	if method in ['on_update', 'on_submit']:
		subject, color = feed_dict.get(doc.doctype, [None, None])
		if subject:
			make_feed('', doc.doctype, doc.name, doc.owner, subject % doc.as_dict(), color)

def make_comment_feed(doc, method):
	"""add comment to feed"""
	comment = doc.comment
	if len(comment) > 240:
		comment = comment[:240] + "..."

	make_feed('Comment', doc.comment_doctype, doc.comment_docname, doc.comment_by,
		'<i>"' + comment + '"</i>', '#6B24B3')

