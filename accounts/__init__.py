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
from webnotes.utils import flt
from webnotes.model.code import get_obj
from accounts.utils import get_balance_on

@webnotes.whitelist()
def get_default_bank_account():
	"""
		Get default bank account for a company
	"""
	company = webnotes.form_dict.get('company')
	if not company: return
	res = webnotes.conn.sql("""\
		SELECT default_bank_account FROM `tabCompany`
		WHERE name=%s AND docstatus<2""", company)
	
	if res: return res[0][0]
