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
from webnotes.model.doc import make_autoname, Document, addchild
# Posts JV

def post_jv(data):
	jv = Document('Journal Voucher')
	jv.voucher_type = data.get('voucher_type')
	jv.naming_series = data.get('naming_series')
	jv.voucher_date = data.get('cheque_date')
	jv.posting_date = data.get('cheque_date')
	jv.cheque_no = data.get('cheque_number')
	jv.cheque_date = data.get('cheque_date')
	jv.fiscal_year = data.get('fiscal_year') # To be modified to take care
	jv.company = data.get('company')

	jv.save(1)

	jc = addchild(jv,'entries','Journal Voucher Detail',0)
	jc.account = data.get('debit_account')
	jc.debit = data.get('amount')
	jc.save()

	jc = addchild(jv,'entries','Journal Voucher Detail',0)
	jc.account = data.get('credit_account')
	jc.credit = data.get('amount')
	jc.save()

	return jv.name