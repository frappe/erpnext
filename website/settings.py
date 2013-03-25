import webnotes

page_map = {
	'Web Page': webnotes._dict({
		"template": 'html/web_page.html',
		"condition_field": "published"
	}),
	'Blog Post': webnotes._dict({
		"template": 'html/blog_page.html',
		"condition_field": "published",
	}),
	'Item': webnotes._dict({
		"template": 'html/product_page.html',
		"condition_field": "show_in_website",
	}),
	'Item Group': webnotes._dict({
		"template": "html/product_group.html",
		"condition_field": "show_in_website"
	})
}

page_settings_map = {
	"about": "website.doctype.about_us_settings.about_us_settings.get_args",
	"contact": "Contact Us Settings",
	"blog": "website.helpers.blog.get_blog_template_args",
	"writers": "website.helpers.blog.get_writers_args",
	"print": "core.doctype.print_format.print_format.get_args",
	"orders": "selling.doctype.sales_order.sales_order.get_currency_and_number_format",
	"order": "selling.doctype.sales_order.sales_order.get_website_args",
	"ticket": "support.doctype.support_ticket.support_ticket.get_website_args"
}

no_cache = ["message", "print", "order", "ticket"]
