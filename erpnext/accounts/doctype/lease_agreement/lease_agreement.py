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
from webnotes.model.doc import make_autoname, Document, addchild
from webnotes import msgprint
from webnotes.utils import get_defaults
import json
from accounts.utils import post_jv
sql = webnotes.conn.sql

class DocType:
	def __init__(self, doc, doclist):
		self.doc, self.doclist = doc, doclist

	def autoname(self):
		"""
			Create Lease Id using naming_series pattern
		"""
		self.doc.name = make_autoname(self.doc.naming_series+ '.#####')

	def lease_installment_post(self, args):
		"""
			Posts the Installment receipt into Journal Voucher
		"""
		next_inst = sql("select amount,name from `tabLease Installment` where parent=%s and ifnull(cheque_number,'')='' order by due_date limit 1",self.doc.name)

		data = json.loads(args)
		data['voucher_type']='Lease Receipt'
		data['naming_series']='JV'
		data['amount']=next_inst[0][0]
		data['debit_account']=data.get('bank_account')
		data['credit_account']=self.doc.account
		data['fiscal_year']=get_defaults()['fiscal_year']
		data['company']=get_defaults()['company']
		jv_name=post_jv(data)

		sql("update `tabLease Installment` set cheque_number=%s, cheque_date=%s, jv_number=%s where name=%s",(data.get('cheque_number'),data.get('cheque_date'),jv_name,next_inst[0][1]))

		self.doclist = [Document(d.doctype, d.name) for d in self.doclist]
