# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, getdate, nowdate, fmt_money
from frappe import msgprint, _
from frappe.model.document import Document

form_grid_templates = {
	"journal_entries": "templates/form_grid/bank_reconciliation_grid.html"
}

class BankReconciliation(Document):
	def get_payment_entries(self):
		if not (self.bank_account and self.from_date and self.to_date):
			msgprint(_("Bank Account, From Date and To Date are Mandatory"))
			return

		condition = ""
		if not self.include_reconciled_entries:
			condition = "and (clearance_date is null or clearance_date='0000-00-00')"


		journal_entries = frappe.db.sql("""
			select 
				"Journal Entry Account" as payment_document, t2.name as payment_entry, 
				t2.cheque_no as cheque_number, t2.cheque_date, 
				t2.debit_in_account_currency as debit, t2.credit_in_account_currency as credit, 
				t1.posting_date, t2.against_account, t2.clearance_date, t2.account_currency 
			from
				`tabJournal Entry` t1, `tabJournal Entry Account` t2
			where
				t2.parent = t1.name and t2.account = %s and t1.docstatus=1
				and t1.posting_date >= %s and t1.posting_date <= %s 
				and ifnull(t1.is_opening, 'No') = 'No' {0}
			order by t1.posting_date ASC, t1.name DESC
		""".format(condition), (self.bank_account, self.from_date, self.to_date), as_dict=1)

		payment_entries = frappe.db.sql("""
			select 
				"Payment Entry" as payment_document, name as payment_entry, 
				reference_no as cheque_number, reference_date as cheque_date, 
				if(paid_from=%(account)s, paid_amount, "") as credit, 
				if(paid_from=%(account)s, "", received_amount) as debit, 
				posting_date, ifnull(party,if(paid_from=%(account)s,paid_to,paid_from)) as against_account, clearance_date,
				if(paid_to=%(account)s, paid_to_account_currency, paid_from_account_currency) as account_currency
			from `tabPayment Entry`
			where
				(paid_from=%(account)s or paid_to=%(account)s) and docstatus=1
				and posting_date >= %(from)s and posting_date <= %(to)s {0}
			order by 
				posting_date ASC, name DESC
		""".format(condition), 
		        {"account":self.bank_account, "from":self.from_date, "to":self.to_date}, as_dict=1)

		pos_entries = []
		if self.include_pos_transactions:
			pos_entries = frappe.db.sql("""
				select
					"Sales Invoice Payment" as payment_document, sip.name as payment_entry, sip.amount as debit,
					si.posting_date, si.debit_to as against_account, sip.clearance_date,
					account.account_currency, 0 as credit
				from `tabSales Invoice Payment` sip, `tabSales Invoice` si, `tabAccount` account
				where
					sip.account=%(account)s and si.docstatus=1 and sip.parent = si.name
					and account.name = sip.account and si.posting_date >= %(from)s and si.posting_date <= %(to)s {0}
				order by
					si.posting_date ASC, si.name DESC
			""".format(condition),
			        {"account":self.bank_account, "from":self.from_date, "to":self.to_date}, as_dict=1)

		entries = sorted(list(payment_entries)+list(journal_entries+list(pos_entries)),
			key=lambda k: k['posting_date'] or getdate(nowdate()))

		self.set('payment_entries', [])
		self.total_amount = 0.0

		for d in entries:
			row = self.append('payment_entries', {})
			amount = d.debit if d.debit else d.credit
			d.amount = fmt_money(amount, 2, d.account_currency) + " " + (_("Dr") if d.debit else _("Cr"))
			d.pop("credit")
			d.pop("debit")
			d.pop("account_currency")
			row.update(d)
			self.total_amount += flt(amount)

	def update_clearance_date(self):
		clearance_date_updated = False
		for d in self.get('payment_entries'):
			if d.clearance_date:
				if not d.payment_document:
					frappe.throw(_("Row #{0}: Payment document is required to complete the trasaction"))

				if d.cheque_date and getdate(d.clearance_date) < getdate(d.cheque_date):
					frappe.throw(_("Row #{0}: Clearance date {1} cannot be before Cheque Date {2}")
						.format(d.idx, d.clearance_date, d.cheque_date))

			if d.clearance_date or self.include_reconciled_entries:
				if not d.clearance_date:
					d.clearance_date = None

				frappe.db.set_value(d.payment_document, d.payment_entry, "clearance_date", d.clearance_date)
				frappe.db.sql("""update `tab{0}` set clearance_date = %s, modified = %s 
					where name=%s""".format(d.payment_document), 
				(d.clearance_date, nowdate(), d.payment_entry))
				
				clearance_date_updated = True

		if clearance_date_updated:
			self.get_payment_entries()
			msgprint(_("Clearance Date updated"))
		else:
			msgprint(_("Clearance Date not mentioned"))
