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
import _mysql_exceptions

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
	reload_doc('utilities', 'page', 'todo')
	reload_doc('utilities', 'page', 'calendar')
	reload_doc('utilities', 'page', 'messages')
	reload_doc('setup', 'page', 'modules_setup')
	reload_doc('utilities', 'page', 'users')
	reload_doc('home', 'page', 'activity')
	reload_doc('home', 'page', 'attributions')
	reload_doc('core', 'doctype', 'profile')
	
	# update user_image in profile
	for p in webnotes.conn.sql("""select name, file_list from tabProfile 
		where ifnull(file_list,'')!=''"""):
		fid = p[1].split('\n')[0].split(',')[1]
		webnotes.conn.set_value('Profile', p[0], 'user_image', fid)
	
	webnotes.conn.set_value('Control Panel', 'Control Panel', 'home_page',
			'desktop')

	webnotes.conn.commit()

	try:
		webnotes.conn.sql("""create table __SchedulerLog (
			`timestamp` timestamp,
			method varchar(200),
			error text
		) engine=MyISAM""")
	except _mysql_exceptions.OperationalError, e:
		pass
