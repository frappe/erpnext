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
	webnotes.reload_doc("support", "doctype", "support_ticket")
	webnotes.reload_doc("core", "doctype", "communication")
	for d in webnotes.conn.sql("""select name, raised_by from `tabSupport Ticket` 
			where docstatus < 2""", as_dict=True):
		tic = webnotes.get_obj("Support Ticket", d.name)
		tic.set_lead_contact(d.raised_by)
		webnotes.conn.sql("""update `tabSupport Ticket` set lead = %s, contact = %s, company = %s 
			where name = %s""", (tic.doc.lead, tic.doc.contact, tic.doc.company, d.name))