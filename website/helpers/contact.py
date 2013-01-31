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
from core.doctype.communication.communication import make

max_communications_per_hour = 300

@webnotes.whitelist(allow_guest=True)
def send_message(subject="Website Query", message="", sender="", status="Open"):
	if not message:
		webnotes.response["message"] = 'Please write something'
		return
		
	if not sender:
		webnotes.response["message"] = 'Email Id Required'
		return

	# make lead / communication
		
	name = webnotes.conn.get_value("Lead", {"email_id": sender}, "name")
	if name:
		lead = webnotes.model_wrapper("Lead", name)
		lead.doc.status = status
		lead.ignore_permissions = True
		lead.save()
	else:
		lead = webnotes.model_wrapper({
			"doctype":"Lead",
			"lead_name": sender,
			"email_id": sender,
			"status": status,
			"source": "Website"
		})
		lead.ignore_permissions = True
		lead.insert()
	
	make(content=message, sender=sender, subject=subject,
		doctype="Lead", name=lead.doc.name, lead=lead.doc.name)

	
	# guest method, cap max writes per hour
	if webnotes.conn.sql("""select count(*) from `tabCommunication`
		where TIMEDIFF(NOW(), modified) < '01:00:00'""")[0][0] > max_communications_per_hour:
		webnotes.response["message"] = "Sorry: we believe we have received an unreasonably high number of requests of this kind. Please try later"
		return
	
	webnotes.response["message"] = 'Thank You'