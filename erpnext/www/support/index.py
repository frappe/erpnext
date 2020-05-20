from __future__ import unicode_literals
import frappe
from frappe.utils import is_markdown, markdown
from frappe.website.utils import get_comment_list

def get_context(context):
	if is_markdown(context.content):
			context.content = markdown(context.content)
		context.login_required = True
		context.category = frappe.get_doc('Help Category', self.category)
		context.level_class = get_level_class(self.level)
		context.comment_list = get_comment_list(self.doctype, self.name)
		context.show_sidebar = True
		context.sidebar_items = get_sidebar_items()
		context.parents = self.get_parents(context)

	def get_parents(self, context):
		return [{"title": context.category.category_name, "route":context.category.route}]
