import webnotes, conf, os
from webnotes.utils import cint, cstr

def get_templates_path():
	return os.path.join(os.path.dirname(conf.__file__), "app", "website", "templates")

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
		"favicon", "facebook_share", "google_plus_one", "twitter_share", "linked_in_share",
		"disable_signup"]:
		if k in settings.fields:
			args[k] = settings.fields.get(k)

	for k in ["facebook_share", "google_plus_one", "twitter_share", "linked_in_share",
		"disable_signup"]:
		args[k] = cint(args.get(k) or 0)
	
	args.url = quote(str(get_request_site_address(full_address=True)), str(""))
	args.encoded_title = quote(str(args.title or ""), str(""))
	
	return args
	