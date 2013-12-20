# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	# reset Page perms
	from core.page.permission_manager.permission_manager import reset
	reset("Page")
	reset("Report")
	
	# patch to move print, email into DocPerm
	for doctype, hide_print, hide_email in webnotes.conn.sql("""select name, ifnull(allow_print, 0), ifnull(allow_email, 0)
		from `tabDocType` where ifnull(issingle, 0)=0 and ifnull(istable, 0)=0 and
		(ifnull(allow_print, 0)=0 or ifnull(allow_email, 0)=0)"""):
		
		if not hide_print:
			webnotes.conn.sql("""update `tabDocPerm` set `print`=1
				where permlevel=0 and `read`=1 and parent=%s""", doctype)
		
		if not hide_email:
			webnotes.conn.sql("""update `tabDocPerm` set `email`=1
				where permlevel=0 and `read`=1 and parent=%s""", doctype)
