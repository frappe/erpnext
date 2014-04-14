# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, flt, getdate, nowdate
from frappe import msgprint, _
from frappe.model.document import Document

class BankReconciliation(Document):
	def get_details(self):
		if not (self.bank_account and self.from_date and self.to_date):
			msgprint("Bank Account, From Date and To Date are Mandatory")
			return

		dl = frappe.db.sql("""select t1.name, t1.cheque_no, t1.cheque_date, t2.debit,
				t2.credit, t1.posting_date, t2.against_account
			from
				`tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where
				t2.parent = t1.name and t2.account = %s
				and (clearance_date is null or clearance_date = '0000-00-00' or clearance_date = '')
				and t1.posting_date >= %s and t1.posting_date <= %s and t1.docstatus=1""",
				(self.bank_account, self.from_date, self.to_date))

		self.set('entries', [])
		self.total_amount = 0.0

		for d in dl:
			nl = self.append('entries', {})
			nl.posting_date = cstr(d[5])
			nl.voucher_id = cstr(d[0])
			nl.cheque_number = cstr(d[1])
			nl.cheque_date = cstr(d[2])
			nl.debit = flt(d[3])
			nl.credit = flt(d[4])
			nl.against_account = cstr(d[6])
			self.total_amount += flt(flt(d[4]) - flt(d[3]))

	def update_details(self):
		vouchers = []
		for d in self.get('entries'):
			if d.clearance_date:
				if d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
					frappe.throw("Clearance Date can not be before Cheque Date (Row #%s)" % d.idx)

				frappe.db.set_value("Journal Voucher", d.voucher_id, "clearance_date", d.clearance_date)
				frappe.db.sql("""update `tabJournal Voucher` set clearance_date = %s, modified = %s
					where name=%s""", (d.clearance_date, nowdate(), d.voucher_id))
				vouchers.append(d.voucher_id)

		if vouchers:
			msgprint("Clearance Date updated in: {0}".format(", ".join(vouchers)))
		else:
			msgprint(_("Clearance Date not mentioned"))
