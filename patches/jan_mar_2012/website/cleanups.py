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
	from webnotes.model import delete_doc
	from webnotes.modules import reload_doc
	delete_doc("DocType", "SSO Control")
	delete_doc("DocType", "WN ERP Client Control")
	delete_doc("DocType", "Production Tips Common")
	delete_doc("DocType", "DocTrigger")
	delete_doc("Page", "Setup Wizard")
	
	# cleanup control panel
	delete_doc("DocType", "Control Panel")
	reload_doc("core", "doctype", "control_panel")
	
	webnotes.conn.sql("""delete from tabSingles
		where field like 'startup_%' and doctype='Control Panel'""")
	webnotes.conn.sql("""delete from __SessionCache""")

	webnotes.conn.commit()

	# DDLs
	# -------------------
	
	webnotes.conn.sql("drop table if exists tabDocTrigger")	

	try: webnotes.conn.sql("""alter table `tabFile Data` drop column blob_content""")
	except: pass
		
	webnotes.conn.sql("""alter table __PatchLog engine=InnoDB""")
	
