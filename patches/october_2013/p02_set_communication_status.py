# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	webnotes.reload_doc("core", "doctype", "communication")
	
	webnotes.conn.sql("""update tabCommunication 
		set sent_or_received= if(ifnull(recipients, '')='', "Received", "Sent")""")