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

def execute():
	"""
		To Hide Net Total, Grand Total Export and Rounded Total Export on checking print hide
		
		Uncheck print_hide for fields:
			net_total, grand_total_export and rounded_total_export
		For DocType(s):
			* Sales Invoice
			* Sales Order
			* Delivery Note
			* Quotation
	"""
	webnotes.conn.sql("""\
		UPDATE tabDocField
		SET print_hide = 0
		WHERE fieldname IN ('net_total', 'grand_total_export', 'rounded_total_export')
		AND parent IN ('Sales Invoice', 'Sales Order', 'Delivery Note', 'Quotation')
	""")
