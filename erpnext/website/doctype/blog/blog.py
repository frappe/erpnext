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

"""
record of files

naming for same name files: file.gif, file-1.gif, file-2.gif etc
"""

import webnotes
import website.utils
import website.web_page

class DocType(website.web_page.Page):
	def __init__(self, d, dl):
		super(DocType, self).__init__('Blog')
		self.doc, self.doclist = d, dl

	def send_emails(self):
		"""send emails to subscribers"""
		if self.doc.email_sent:
			webnotes.msgprint("""Blog Subscribers already updated""", raise_exception=1)
		
		from webnotes.utils.email_lib.bulk import send
		from markdown2 import markdown
		import webnotes.utils
		
		# get leads that are subscribed to the blog
		recipients = [e[0] for e in webnotes.conn.sql("""select distinct email_id from tabLead where
			ifnull(blog_subscriber,0)=1""")]

		# make heading as link
		content = '<h2><a href="%s/%s.html">%s</a></h2>\n\n%s' % (webnotes.utils.get_request_site_address(),
			self.doc.page_name, self.doc.title, markdown(self.doc.content))

		# send the blog
		send(recipients = recipients, doctype='Lead', email_field='email_id',
			first_name_field = 'lead_name', last_name_field="", subject=self.doc.title,
			message = markdown(content))
		
		webnotes.conn.set(self.doc, 'email_sent', 1)
		webnotes.msgprint("""Scheduled to send to %s subscribers""" % len(recipients))

	def on_update(self):
		super(DocType, self).on_update()
		if not webnotes.utils.cint(self.doc.published):
			self.delete_web_cache(self.doc.page_name)
		else:
			import website.blog
			website.blog.get_blog_content(self.doc.page_name)

	def prepare_template_args(self):
		import webnotes.utils
		
		# this is for double precaution. usually it wont reach this code if not published
		if not webnotes.utils.cint(self.doc.published):
			raise Exception, "This blog has not been published yet!"
		
		# temp fields
		from webnotes.utils import global_date_format, get_fullname
		self.doc.full_name = get_fullname(self.doc.owner)
		self.doc.updated = global_date_format(self.doc.creation)

		self.markdown_to_html(['content'])

		comment_list = webnotes.conn.sql("""\
			select comment, comment_by_fullname, creation
			from `tabComment` where comment_doctype="Blog"
			and comment_docname=%s order by creation""", self.doc.name, as_dict=1)
		
		self.doc.comment_list = comment_list or []
		for comment in self.doc.comment_list:
			comment['comment_date'] = webnotes.utils.pretty_date(comment['creation'])