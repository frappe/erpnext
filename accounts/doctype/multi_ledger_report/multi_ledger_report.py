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
import webnotes
from webnotes.utils import add_days, cint, cstr, flt, getdate
from webnotes.model.doclist import getlist
from webnotes.model.code import get_obj
from webnotes import session, form, msgprint, errprint

sql = webnotes.conn.sql
get_value = webnotes.conn.get_value

#---------------------------------------------------------------------

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	# Get fiscal year based on date
	def get_year(self, dt):
		yr = sql("select name from `tabFiscal Year` where %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day)",dt)
		return yr and yr[0][0] or ''


	def validate_date(self):
		"""check for from date and to date within same year"""
		if not sql("select name from `tabFiscal Year` where %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day) and %s between year_start_date and date_sub(date_add(year_start_date,interval 1 year), interval 1 day)",(self.doc.from_date, self.doc.to_date)):
			msgprint("From Date and To Date must be within same year")
			raise Exception

		if not self.doc.from_date or not self.doc.to_date:
			msgprint("From Date and To Date is mandatory")
			raise Exception

	
	def add_header(self):
		title = 'Ledger Balances Between ' + getdate(self.doc.from_date).strftime('%d-%m-%Y') + ' and ' + getdate(self.doc.to_date).strftime('%d-%m-%Y')
		return [[title], ['Account', 'Posting Date', 'Voucher Type', 'Voucher No', 'Debit', 'Credit', 'Remarks']]
		


	def get_account_subtree(self, acc):		
		return sql("""
			SELECT 
				CONCAT(REPEAT('     ', COUNT(parent.name) - (sub_tree.depth + 1)), node.name) as account, 
				node.lft AS lft, node.rgt AS rgt, 
				node.debit_or_credit as dr_or_cr, node.group_or_ledger as group_or_ledger, node.is_pl_account as is_pl_account
			FROM tabAccount AS node,
				tabAccount AS parent,
				tabAccount AS sub_parent,
				(
					SELECT node.name, (COUNT(parent.name) - 1) AS depth
					FROM tabAccount AS node, tabAccount AS parent
					WHERE node.lft BETWEEN parent.lft AND parent.rgt
					AND node.name = %s
					GROUP BY node.name
					ORDER BY node.lft
			    )AS sub_tree
			WHERE node.lft BETWEEN parent.lft AND parent.rgt
		        AND node.lft BETWEEN sub_parent.lft AND sub_parent.rgt
				AND sub_parent.name = sub_tree.name
			GROUP BY node.name
			ORDER BY node.lft""", acc, as_dict = 1, as_utf8=1)



	def get_acc_summary(self, glc, acc_det):
		from_date_year = self.get_year(add_days(self.doc.from_date, -1))
		to_date_year = self.get_year(self.doc.to_date)
		acc = acc_det['account'].strip()

		if from_date_year == to_date_year:
			debit_on_fromdate, credit_on_fromdate, opening = glc.get_as_on_balance(acc, from_date_year, add_days(self.doc.from_date, -1), acc_det['dr_or_cr'], acc_det['lft'], acc_det['rgt']) # opening = closing of prev_date
		elif acc_det['is_pl_account'] == 'No': # if there is no previous year in system and not pl account
			opening = sql("select opening from `tabAccount Balance` where account = %s and period = %s", (acc, to_date_year))
			debit_on_fromdate, credit_on_fromdate, opening = 0, 0, flt(opening[0][0])
		else: # if pl account and there is no previous year in system
			debit_on_fromdate, credit_on_fromdate, opening = 0,0,0
		
		# closing balance
		#--------------------------------
		debit_on_todate, credit_on_todate, closing = glc.get_as_on_balance(acc, to_date_year, self.doc.to_date, acc_det['dr_or_cr'], acc_det['lft'], acc_det['rgt']) 

		# transaction betn the period
		#----------------------------------------
		debit = flt(debit_on_todate) - flt(debit_on_fromdate)
		credit = flt(credit_on_todate) - flt(credit_on_fromdate)
	
		# Debit / Credit
		if acc_det['dr_or_cr'] == 'Credit':
			opening, closing = -1*opening, -1*closing

		return flt(opening>0 and opening or 0), flt(opening<0 and -opening or 0), \
			debit, credit, flt(closing>0.01 and closing or 0), flt(closing<-0.01 and -closing or 0)


	def show_gl_entries(self, acc):
		"""Get gl entries for the period and account"""
		gle = sql("select posting_date, voucher_type, voucher_no, debit, credit, remarks from `tabGL Entry` WHERE account = %s and posting_date >= %s AND posting_date <= %s and ifnull(is_opening,	'No') = 'No' and ifnull(is_cancelled, 'No') = 'No'", (acc, self.doc.from_date, self.doc.to_date), as_dict=1, as_utf8=1)
		entries, dr, cr = [], 0, 0
		for d in gle:
			entries.append(['', d['posting_date'], d['voucher_type'], d['voucher_no'], d['debit'], d['credit'], d['remarks']])
		return entries




	# Get Report Data
	def get_report_data(self):
		self.validate_date()

		res = []
		res += self.add_header()

		glc = get_obj('GL Control')

		for d in getlist(self.doclist, 'ledger_details'):
			# Fetch acc details
			sub_tree = self.get_account_subtree(d.account)

			for acc_det in sub_tree:
				acc_summary = self.get_acc_summary(glc, acc_det)
				if acc_summary[0] or acc_summary[1] or acc_summary[2] or acc_summary[3] or acc_summary[4] or acc_summary[5]:
					res.append([acc_det['account']])
					# Show gl entries if account is ledger
					if acc_det['group_or_ledger'] == 'Ledger' and (acc_summary[2] or acc_summary[3]):
						gle = self.show_gl_entries(acc_det['account'].strip())
						res += gle
	
					# Totals
					res.append(['', '', '', 'Total Debit/Credit', acc_summary[2], acc_summary[3]])
					res.append(['', '', '', 'Opening Balance', acc_summary[0], acc_summary[1]])
					res.append(['', '', '', 'Closing Balance', acc_summary[4], acc_summary[5]])

		return res
