import webnotes, conf, os
from webnotes.utils import cint, cstr, encode

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
	args.encoded_title = quote(encode(args.title or ""), str(""))
	args.shopping_cart_enabled = cint(webnotes.conn.get_default("shopping_cart_enabled"))
	
	return args
	
@webnotes.whitelist()
def update_profile(fullname, password=None, company_name=None, mobile_no=None, phone=None):
	from website.helpers.cart import update_party
	update_party(fullname, company_name, mobile_no, phone)
	
	from core.doctype.profile import profile
	return profile.update_profile(fullname, password)
	
def get_profile_args():
	from website.helpers.cart import get_lead_or_customer
	party = get_lead_or_customer()
	if party.doctype == "Lead":
		mobile_no = party.mobile_no
		phone = party.phone
	else:
		mobile_no, phone = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user, 
			"customer": party.name})
		
	return {
		"company_name": party.customer_name if party.doctype == "Customer" else party.company_name,
		"mobile_no": mobile_no,
		"phone": phone
	}