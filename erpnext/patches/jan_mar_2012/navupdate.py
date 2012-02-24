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

import webnotes

def execute():
	from webnotes.modules import reload_doc
	reload_doc('accounts', 'page', 'accounts_home')
	reload_doc('selling', 'page', 'selling_home')
	reload_doc('buying', 'page', 'buying_home')
	reload_doc('stock', 'page', 'stock_home')
	reload_doc('hr', 'page', 'hr_home')
	reload_doc('support', 'page', 'support_home')
	reload_doc('production', 'page', 'production_home')
	reload_doc('projects', 'page', 'projects_home')
	reload_doc('website', 'page', 'website_home')
	reload_doc('home', 'page', 'desktop')
	
	webnotes.conn.commit()
	webnotes.conn.sql("""create table __SchedulerLog (
		`timestamp` timestamp,
		method varchar(200),
		error text
	) engine=MyISAM""")
