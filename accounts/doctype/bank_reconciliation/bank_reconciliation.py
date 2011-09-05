# Please edit this list and import only required elements
import webnotes

from webnotes.utils import add_days, add_months, add_years, cint, cstr, date_diff, default_fields, flt, fmt_money, formatdate, generate_hash, getTraceback, get_defaults, get_first_day, get_last_day, getdate, has_common, month_name, now, nowdate, replace_newlines, sendmail, set_default, str_esc_quote, user_format, validate_email_add
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, removechild, getchildren, make_autoname, SuperDocType
from webnotes.model.doclist import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, is_testing, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def get_details(self):
		if not (self.doc.bank_account and self.doc.from_date and self.doc.to_date):
			msgprint("Bank Account, From Date and To Date are Mandatory")
			return
	
		dl = sql("select t1.name, t1.cheque_no, t1.cheque_date, t2.debit, t2.credit, t1.posting_date, t2.against_account from `tabJournal Voucher` t1, `tabJournal Voucher Detail` t2 where t2.parent = t1.name and t2.account = %s and (clearance_date is null or clearance_date = '0000-00-00' or clearance_date = '') and (t1.cheque_no is not null or t1.cheque_no != '') and t1.posting_date >= %s and t1.posting_date <= %s and t1.docstatus=1", (self.doc.bank_account, self.doc.from_date, self.doc.to_date))
		
		self.doc.clear_table(self.doclist, 'entries')
		self.doc.total_amount = 0.0

		for d in dl:
			nl = addchild(self.doc, 'entries', 'Bank Reconciliation Detail', 1, self.doclist)
			nl.posting_date = str(d[5])
			nl.voucher_id = str(d[0])
			nl.cheque_number = str(d[1])
			nl.cheque_date = str(d[2])
			nl.debit = flt(d[3])
			nl.credit = flt(d[4])
			nl.against_account = d[6]
			self.doc.total_amount += flt(flt(d[4]) - flt(d[3]))

	def update_details(self):
		for d in getlist(self.doclist, 'entries'):
			if d.clearance_date:
				sql("update `tabJournal Voucher` set clearance_date = %s, modified = %s where name=%s", (d.clearance_date, nowdate(), d.voucher_id))
		msgprint("Updated")
