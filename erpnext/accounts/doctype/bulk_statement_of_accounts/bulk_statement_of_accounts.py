# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.accounts.report.general_ledger.general_ledger import execute as get_soa
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import execute as get_ageing
from frappe.core.doctype.communication.email import make

from frappe.utils.print_format import report_to_pdf
from frappe.utils.pdf import get_pdf
from frappe.utils import today, add_days, getdate, format_date
from datetime import timedelta

days_to_add = {	'Every Week': 7, 'Every Month': 30, 'Every Quarter': 91 }

class BulkStatementOfAccounts(Document):
	def validate(self):
		if not self.customer_list:
			frappe.throw(frappe._('Customers not selected!'))

		global days_to_add
		if self.frequency != '':
			self.from_date = self.start_date
			self.to_date = add_days(self.start_date, days_to_add[self.frequency])

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

def get_report_pdf(doc, consolidated=True):
	statement_dict = {}
	aging = ''
	base_template_path = "frappe/www/printview.html"

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

	for entry in doc.customer_list:
		if doc.include_ageing:
			ageing_filters = frappe._dict({
				'company': doc.company,
				'report_date': doc.to_date,
				'ageing_based_on': doc.ageing_based_on,
				'range1': 30,
				'range2': 60,
				'range3': 90,
				'range4': 120,
				'customer': entry.customer
			})
			col1, aging = get_ageing(ageing_filters)
			aging[0]['ageing_based_on'] = doc.ageing_based_on
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
			'show_cancelled_entries': 0,
			'tax_id': tax_id if tax_id else ''
		})
		col, res = get_soa(filters)
		html = frappe.render_template('accounts/doctype/bulk_statement_of_accounts/bsoa.html', \
			{ "filters": filters, "data": res, "aging": aging[0] if doc.include_ageing else None})
		html = frappe.render_template(base_template_path, {"body": ''.join(html), "title": "Statement For " + entry.customer})
		statement_dict[entry.customer] = html

	if consolidated:
		result = ''.join(list(statement_dict.values()))
		return get_pdf(result, {'orientation': doc.orientation})
	else:
		for customer, statement_html in statement_dict.items():
			statement_dict[customer]=get_pdf(statement_html, {'orientation': doc.orientation})
		return statement_dict

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

@frappe.whitelist()
def manual_email_send(document_name):
	doc = frappe.get_doc('Bulk Statement Of Accounts', document_name)
	for customer, report_pdf in get_report_pdf(doc, consolidated=False).items():
		attachment = {
			'fname': customer + '.pdf',
			'fcontent': report_pdf
		}
		frappe.enqueue(
			queue='short',
			job_name=doc.name + ':' + format_date(doc.from_date) + '-' + format_date(doc.to_date),
			method=frappe.sendmail,
			recipients=[frappe.get_value('Customer', customer, 'email_id')],
			sender=frappe.session.user,
			subject='Statement Of Account for '+customer,
			message='Hi '+customer,
			reference_doctype='Bulk Statement Of Accounts',
			reference_name=document_name,
			attachments=[attachment]
		)

def auto_email_soa():
	selected = frappe.get_list('Bulk Statement Of Accounts', filter={'to_date': format_date(today())})

	for entry in selected:
		manual_email_send(entry.name)
		doc = frappe.get_doc('Bulk Statement Of Accounts', entry.name)
		doc.from_date = doc.to_date
		doc.to_date = add_days(doc.to_date, days_to_add[doc.frequency])
		doc.save()
	frappe.db.commit()