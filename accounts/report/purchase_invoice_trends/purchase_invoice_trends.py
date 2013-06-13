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
from webnotes.utils import cint, add_days, add_months, cstr
from controllers.trends	import get_columns,get_data

def execute(filters=None):
	if not filters: filters ={}
	data = []

	trans = "Purchase Invoice"
	tab = ["tabPurchase Invoice","tabPurchase Invoice Item"]
	ysd = webnotes.conn.sql("select year_start_date from `tabFiscal Year` where name = '%s'"%filters.get("fiscal_year"))[0][0]
	year_start_date = ysd.strftime('%Y-%m-%d')
	start_month = cint(year_start_date.split('-')[1])

	columns, query_bon, query_pwc, basedon, grbc, sup_tab = get_columns(filters, year_start_date, start_month, trans)
	data = get_data(columns,filters, tab, query_bon, query_pwc, basedon, grbc ,sup_tab)

	if data == '':
		webnotes.msgprint("Data Not Available")
	return columns, data 