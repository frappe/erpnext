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

@webnotes.whitelist()
def subscribe(arg):
	"""subscribe to blog (blog_subscriber)"""
	if webnotes.conn.sql("""select name from `tabBlog Subscriber` where name=%s""", arg):
		webnotes.msgprint("Already a subscriber. Thanks!")
	else:
		from webnotes.model.doc import Document
		d = Document('Blog Subscriber')
		d.name = arg
		d.save()
		webnotes.msgprint("Thank you for subscribing!")