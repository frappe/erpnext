# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
from frappe.model.document import Document

class CForm(Document):
	def validate(self):
		"""Validate invoice that c-form is applicable
			and no other c-form is received for that"""

		for d in self.get('invoice_details'):
			if d.invoice_no:
				inv = frappe.db.sql("""select c_form_applicable, c_form_no from
					`tabSales Invoice` where name = %s and docstatus = 1""", d.invoice_no)

				if inv and inv[0][0] != 'Yes':
					frappe.throw("C-form is not applicable for Invoice: %s" % d.invoice_no)

				elif inv and inv[0][1] and inv[0][1] != self.name:
					frappe.throw("""Invoice %s is tagged in another C-form: %s.
						If you want to change C-form no for this invoice,
						please remove invoice no from the previous c-form and then try again""" %
						(d.invoice_no, inv[0][1]))

				elif not inv:
					frappe.throw("Row %s: Invoice %s is invalid, it might be cancelled / does not exist. \
						Please enter a valid Invoice" % d.idx, d.invoice_no)

	def on_update(self):
		"""	Update C-Form No on invoices"""
		self.set_total_invoiced_amount()

	def on_submit(self):
		self.set_cform_in_sales_invoices()

	def before_cancel(self):
		# remove cform reference
		frappe.db.sql("""update `tabSales Invoice` set c_form_no=null where c_form_no=%s""", self.name)

	def set_cform_in_sales_invoices(self):
		inv = [d.invoice_no for d in self.get('invoice_details')]
		if inv:
			frappe.db.sql("""update `tabSales Invoice` set c_form_no=%s, modified=%s where name in (%s)""" %
				('%s', '%s', ', '.join(['%s'] * len(inv))), tuple([self.name, self.modified] + inv))

			frappe.db.sql("""update `tabSales Invoice` set c_form_no = null, modified = %s
				where name not in (%s) and ifnull(c_form_no, '') = %s""" %
				('%s', ', '.join(['%s']*len(inv)), '%s'), tuple([self.modified] + inv + [self.name]))
		else:
			frappe.throw(_("Please enter atleast 1 invoice in the table"))

	def set_total_invoiced_amount(self):
		total = sum([flt(d.grand_total) for d in self.get('invoice_details')])
		frappe.db.set(self, 'total_invoiced_amount', total)

	def get_invoice_details(self, invoice_no):
		"""	Pull details from invoices for referrence """
		if invoice_no:
			inv = frappe.db.get_value("Sales Invoice", invoice_no,
				["posting_date", "territory", "net_total", "grand_total"], as_dict=True)
			return {
				'invoice_date' : inv.posting_date,
				'territory'    : inv.territory,
				'net_total'    : inv.net_total,
				'grand_total'  : inv.grand_total
			}
