import webnotes, conf, os


def get_templates_path():
	return os.path.join(os.path.dirname(conf.__file__), "app", "website", "templates")

standard_pages = [
	"404", "about", "account", "attributions", "blog", "contact", "error", "index",
	"login", "message", "order", "orders", "print", "product_search", "profile",
	"ticket", "tickets", "writers"
]

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

def get_home_page():
	doc_name = webnotes.conn.get_value('Website Settings', None, 'home_page')
	if doc_name:
		page_name = webnotes.conn.get_value('Web Page', doc_name, 'page_name')
	else:
		page_name = 'login'

	return page_name

def update_template_args(page_name, args):
	
	from webnotes.utils import get_request_site_address
	from urllib import quote
	
	all_top_items = webnotes.conn.sql("""\
		select * from `tabTop Bar Item`
		where parent='Website Settings' and parentfield='top_bar_items'
		order by idx asc""", as_dict=1)
	
	top_items = [d for d in all_top_items if not d['parent_label']]
	
	# attach child items to top bar
	for d in all_top_items:
		if d['parent_label']:
			for t in top_items:
				if t['label']==d['parent_label']:
					if not 'child_items' in t:
						t['child_items'] = []
					t['child_items'].append(d)
					break
	
	if top_items and ("products" in [d.url.split(".")[0] for d in top_items if d.url]):
		# product categories
		products = webnotes.conn.sql("""select t1.item_group as label, 
			t2.page_name as url,
			ifnull(t1.indent,0) as indent
			from `tabWebsite Product Category` t1, `tabItem Group` t2 
			where t1.item_group = t2.name
			and ifnull(t2.show_in_website,0)=1 order by t1.idx""", as_dict=1)
		products_item = filter(lambda d: d.url and d.url.split(".")[0]=="products", top_items)[0]			
		products_item.child_items = products
		
	ret = webnotes._dict({
		'top_bar_items': top_items,
		'footer_items': webnotes.conn.sql("""\
			select * from `tabTop Bar Item`
			where parent='Website Settings' and parentfield='footer_items'
			order by idx asc""", as_dict=1),
			
		'int':int,
		"webnotes": webnotes,
		"utils": webnotes.utils
	})
	
	args.update(ret)
	
	settings = webnotes.doc("Website Settings", "Website Settings")
	for k in ["banner_html", "brand_html", "copyright", "address", "twitter_share_via",
		"favicon", "facebook_share", "google_plus_one", "twitter_share", "linked_in_share"]:
		if k in settings.fields:
			args[k] = settings.fields.get(k)

	for k in ["facebook_share", "google_plus_one", "twitter_share", "linked_in_share"]:
		args[k] = int(args.get(k) or 0)
	
	args.url = quote(str(get_request_site_address(full_address=True)), str(""))
	args.encoded_title = quote(str(args.title or ""), str(""))
	
	return args
	