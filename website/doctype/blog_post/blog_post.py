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
import website.utils
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def autoname(self):
		from website.utils import page_name
		self.doc.name = page_name(self.doc.title)

	def validate(self):
		if self.doc.blog_intro:
			self.doc.blog_intro = self.doc.blog_intro[:140]

		# update posts
		webnotes.conn.sql("""update tabBlogger set posts=(select count(*) from `tabBlog Post` 
			where ifnull(blogger,'')=tabBlogger.name)
			where name=%s""", self.doc.blogger)

	def on_update(self):
		website.utils.update_page_name(self.doc, self.doc.title)
		website.utils.delete_page_cache("writers")

	def send_emails(self):
		"""send emails to subscribers"""
		if self.doc.email_sent:
			webnotes.msgprint("""Blog Subscribers already updated""", raise_exception=1)
		
		from webnotes.utils.email_lib.bulk import send
		import webnotes.utils
		
		# get leads that are subscribed to the blog
		recipients = [e[0] for e in webnotes.conn.sql("""select distinct email_id from 
			tabLead where ifnull(blog_subscriber,0)=1""")]

		# make heading as link
		content = '<h2><a href="%s/%s.html">%s</a></h2>\n\n%s' % (webnotes.utils.get_request_site_address(),
			self.doc.page_name, self.doc.title, self.doc.content)

		# send the blog
		send(recipients = recipients, doctype='Lead', email_field='email_id',
			subject=self.doc.title, message = content)
		
		webnotes.conn.set(self.doc, 'email_sent', 1)
		webnotes.msgprint("""Scheduled to send to %s subscribers""" % len(recipients))

	def prepare_template_args(self):
		import webnotes.utils
		
		# this is for double precaution. usually it wont reach this code if not published
		if not webnotes.utils.cint(self.doc.published):
			raise Exception, "This blog has not been published yet!"
		
		# temp fields
		from webnotes.utils import global_date_format, get_fullname
		self.doc.full_name = get_fullname(self.doc.owner)
		self.doc.updated = global_date_format(self.doc.published_on)
		self.doc.content_html = self.doc.content
		if self.doc.blogger:
			self.doc.blogger_info = webnotes.doc("Blogger", self.doc.blogger).fields
			if self.doc.blogger_info.avatar and not "/" in self.doc.blogger_info.avatar:
				self.doc.blogger_info.avatar = "files/" + self.doc.blogger_info.avatar
		
		self.doc.description = self.doc.blog_intro or self.doc.content[:140]
		
		self.doc.categories = webnotes.conn.sql_list("select name from `tabBlog Category` order by name")
		
		self.doc.texts = {
			"comments": _("Comments"),
			"first_comment": _("Be the first one to comment"),
			"add_comment": _("Add Comment"),
			"submit": _("Submit"),
			"all_posts_by": _("All posts by"),
		}

		comment_list = webnotes.conn.sql("""\
			select comment, comment_by_fullname, creation
			from `tabComment` where comment_doctype="Blog Post"
			and comment_docname=%s order by creation""", self.doc.name, as_dict=1)
		
		self.doc.comment_list = comment_list or []
		for comment in self.doc.comment_list:
			comment['comment_date'] = webnotes.utils.global_date_format(comment['creation'])
