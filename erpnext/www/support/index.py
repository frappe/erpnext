from __future__ import unicode_literals
import frappe
from frappe import _

def get_context(context):
	support_settings = frappe.get_single("Support Settings")
	print(support_settings.enable_support_portal)
	if not support_settings.enable_support_portal:
		print('inside')
		# raise frappe.PermissionError
		# return frappe.respond_as_web_page(_("Not available"), _("This page is not available"),
		# 	indicator_color='red')
		frappe.respond_as_web_page(title="Not available", html="This page is not available", indicator_color="red")
		# return frappe.website.render.render("message", http_status_code=404)
		return
		# raise frappe.PermissionError
	favorite_article_count = 0
	portal_setting = frappe.get_single("Portal Settings")
	context.favorite_article_list=[]
	context.help_article_list=[]
	context.category_list = frappe.get_all("Help Category", fields="name")
	all_articles = [i[0] for i in frappe.db.sql("""SELECT route from `tabHelp Article`""")]
	favorite_articles = frappe.db.sql(
		"""SELECT path, COUNT(*)
			FROM `tabWeb Page View`
			GROUP BY path
			ORDER BY COUNT(*) DESC""")
	for article in favorite_articles:
		favorite_article_dict = {}
		if favorite_article_count < 3:
			if article[0] in all_articles:
				favorite_article = frappe.get_all("Help Article", fields=["title", "content", "route", "category"], filters={"route": article[0]})
				content = frappe.utils.strip_html(favorite_article[0].content)
				if len(content) > 115:
					content = content[:112] + '...'	
				favorite_article_dict = {
					'title': favorite_article[0].title,
					'content': content,
					'category': favorite_article[0].category,
					'route': favorite_article[0].route,
				}
				context.favorite_article_list.append(favorite_article_dict)
				favorite_article_count += 1			

	for category in context.category_list:
		help_aricles_per_category = {}
		help_articles = frappe.get_all("Help Article", fields="*", filters={"category": category.name}, order_by="modified desc", limit=5)
		help_aricles_per_caetgory = {
			'category': category,
			'articles': help_articles,
		}
		context.help_article_list.append(help_aricles_per_caetgory)