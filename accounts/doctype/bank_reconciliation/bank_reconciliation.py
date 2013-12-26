# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr, flt, getdate, now, nowdate
from webnotes.model import db_exists
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist, copy_doclist
from webnotes import msgprint, _
	


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_details(self):
		if not (self.doc.bank_account and self.doc.from_date and self.doc.to_date):
			msgprint(_("Bank Account, From Date and To Date are Mandatory"))
			return
	
		dl = webnotes.conn.sql("select t1.name, t1.cheque_no, t1.cheque_date, t2.debit, t2.credit, t1.posting_date, t2.against_account from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 where t2.parent = t1.name and t2.account = %s and (clearance_date is null or clearance_date = '0000-00-00' or clearance_date = '') and t1.posting_date >= %s and t1.posting_date <= %s and t1.docstatus=1", (self.doc.bank_account, self.doc.from_date, self.doc.to_date))
		
		self.doclist = self.doc.clear_table(self.doclist, 'entries')
		self.doc.total_amount = 0.0

		for d in dl:
			nl = addchild(self.doc, 'entries', 'Bank Reconciliation Detail', self.doclist)
			nl.posting_date = cstr(d[5])
			nl.voucher_id = cstr(d[0])
			nl.cheque_number = cstr(d[1])
			nl.cheque_date = cstr(d[2])
			nl.debit = flt(d[3])
			nl.credit = flt(d[4])
			nl.against_account = cstr(d[6])
			self.doc.total_amount += flt(flt(d[4]) - flt(d[3]))

	def update_details(self):
		vouchers = []
		for d in getlist(self.doclist, 'entries'):
			if d.clearance_date:
				if d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
					msgprint(_("Clearance Date can not be before Cheque Date (Row #%(row_id)s)") % 
						dict(row_id=d.idx), raise_exception=1)
					
				webnotes.conn.sql("""update `tabJournal Voucher` 
					set clearance_date = %s, modified = %s where name=%s""",
					(d.clearance_date, nowdate(), d.voucher_id))
				vouchers.append(d.voucher_id)

		if vouchers:
			msgprint(_("Clearance Date updated in %(update_date)s") % dict(update_date=", ".join(vouchers)))
		else:
			msgprint(_("Clearance Date not mentioned"))