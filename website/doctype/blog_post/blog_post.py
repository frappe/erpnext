# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
import webnotes.webutils
from webnotes import _

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl

	def autoname(self):
		from webnotes.webutils import page_name
		self.doc.name = page_name(self.doc.title)

	def validate(self):
		if self.doc.blog_intro:
			self.doc.blog_intro = self.doc.blog_intro[:140]

		# update posts
		webnotes.conn.sql("""update tabBlogger set posts=(select count(*) from `tabBlog Post` 
			where ifnull(blogger,'')=tabBlogger.name)
			where name=%s""", self.doc.blogger)

	def on_update(self):
		webnotes.webutils.update_page_name(self.doc, self.doc.title)
		webnotes.webutils.delete_page_cache("writers")

	def prepare_template_args(self):
		import webnotes.utils
		import markdown2
		
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
		
		self.doc.description = self.doc.blog_intro or self.doc.content[:140]
		self.doc.meta_description = self.doc.description
		
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
			comment['comment'] = markdown2.markdown(comment['comment'])
