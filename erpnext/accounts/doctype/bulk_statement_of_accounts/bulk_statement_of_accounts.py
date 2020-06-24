# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.accounts.report.general_ledger.general_ledger import execute
from frappe.utils.print_format import report_to_pdf
from frappe.utils.pdf import get_pdf
from frappe.utils import today, add_days, getdate
from datetime import timedelta

class BulkStatementOfAccounts(Document):
	def validate(self):
		if not self.customer_list:
			frappe.throw(frappe._('Customers not selected!'))

		if self.frequency != '':
			self.is_autoemail = 1
			frappe.db.commit()

	def send_mail(self):
		attachment = {
			'fname': 'Statement Of Accounts',
			'fcontent': self.get_report_pdf()
		}
		# In Loop
		frappe.sendmail(
			recipients=[ 'customer@email.com '],
			sender = frappe.session.user,
			subject= 'Statement Of Accs',
			message= 'Something',
			reference_doctype=self.doctype,
			reference_name=self.name,
			attachments=attachments
		)

def get_report_pdf(doc):
	if doc.frequency != '':
		to_add = 0
		if doc.frequency == 'Every Week':
			to_add = -7
		elif doc.frequency == 'Every Month':
			to_add = -30
		elif doc.frequency == 'Every Quarter':
			to_add = -91
		doc.from_date = add_days(doc.from_date, to_add)
		doc.to_date = getdate(today())

	total_html = []
	for entry in doc.customer_list:
		tax_id = frappe.get_doc('Customer', entry.customer).tax_id
		filters= frappe._dict({
			'from_date': doc.from_date,
			'to_date': doc.to_date,
			'company': doc.company,
			'finance_book': doc.finance_book if doc.finance_book else '',
			'account': doc.account if doc.account else '',
			'voucher_number': doc.voucher_number if doc.voucher_number else '',
			'party_type': 'Customer',
			'party': [entry.customer],
			'group_by': doc.group_by,
			'currency': doc.currency,
			'cost_center': [doc.cost_center] if doc.cost_center else [],
			'project': [doc.project] if doc.project else [],
			'show_opening_entries': 'No',
			'include_default_book_entries': 0,
			'show_cancelled_entries': 1,
			'tax_id': tax_id if tax_id else ''
		})
		col, res = execute(filters)

		total_html.append(
			frappe.render_template('accounts/doctype/bulk_statement_of_accounts/bsoa.html', \
			{ "filters": filters, "data": res}) \
		)
	base_template_path = "frappe/www/printview.html"
	total_html = frappe.render_template(base_template_path, {"body": ''.join(total_html), "title": "Consolidated"})
	return get_pdf(total_html, {'orientation': doc.orientation})

@frappe.whitelist()
def get_customers_based_on_sales_person(sales_person):
	lft, rgt = frappe.db.get_value("Sales Person",
		sales_person, ["lft", "rgt"])

	records = frappe.db.sql("""
		select distinct parent, parenttype
		from `tabSales Team` steam
		where parenttype = 'Customer'
			and exists(select name from `tabSales Person` where lft >= %s and rgt <= %s and name = steam.sales_person)
	""", (lft, rgt), as_dict=1)

	sales_person_records = frappe._dict()
	for d in records:
		sales_person_records.setdefault(d.parenttype, set()).add(d.parent)

	return sales_person_records

@frappe.whitelist()
def download_statements(document_name):
	doc = frappe.get_doc('Bulk Statement Of Accounts', document_name)
	frappe.local.response.filename = doc.name + '.pdf'
	frappe.local.response.filecontent = get_report_pdf(doc)
	frappe.local.response.type = "download"


def auto_email_soa():
	data = frappe.db.sql("""
		SELECT name, frequency, start_date FROM `tabBulk Statement Of Accounts`
		WHERE is_autoemail = 1
	""")