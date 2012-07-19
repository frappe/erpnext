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
def execute():
	import webnotes
	webnotes.conn.sql("""delete from `tabDefaultValue` where defkey in ('page_break', 'projects', 'packing_details', 'discounts', 'brands', 'item_batch_nos', 'after_sales_installations', 'item_searial_nos', 'item_group_in_details', 'exports', 'imports', 'item_advanced', 'sales_extras', 'more_info', 'quality', 'manufacturing', 'pos', 'item_serial_nos', 'purchase_discounts', 'recurring_invoice') and parent = 'Control Panel'""")
