import webnotes

@webnotes.whitelist(allow_guest=True)
def get_product_list(args=None):
	"""
		args = {
			'limit_start': 0,
			'limit_page_length': 20,
			'search': '',
			'product_group': '',
		}
	"""
	import webnotes
	from webnotes.utils import cstr, cint
	
	if not args: args = webnotes.form_dict
	
	# base query
	query = """\
		select name, item_name, page_name, website_image,
		description, web_short_description
		from `tabItem`
		where is_sales_item = 'Yes'
		and docstatus = 0
		and show_in_website = 1"""
	
	# search term condition
	if args.get('search'):
		query += """
			and (
				web_short_description like %(search)s or
				web_long_description like %(search)s or
				description like %(search)s or
				item_name like %(search)s or
				name like %(search)s
			)"""
		args['search'] = "%" + cstr(args.get('search')) + "%"
	
	# product group condition
	if args.get('product_group') and args.get('product_group') != 'All Products':
		query += """
			and item_group = %(product_group)s"""
	
	# order by
	query += """
		order by item_name asc, name asc"""

	from webnotes.widgets.query_builder import add_limit_to_query
	query, args = add_limit_to_query(query, args)

	return webnotes.conn.sql(query, args, as_dict=1)

@webnotes.whitelist(allow_guest=True)
def get_product_category_list(args=None):
	"""
		args = {
			'limit_start': 0,
			'limit_page_length': 5,
		}
	"""
	import webnotes
	
	if not args: args = webnotes.form_dict
	
	query = """\
		select count(name) as items, item_group
		from `tabItem`
		where is_sales_item = 'Yes'
		and docstatus = 0
		and show_in_website = 1
		group by item_group
		order by items desc"""
		
	from webnotes.widgets.query_builder import add_limit_to_query
	query, args = add_limit_to_query(query, args)

	
	result = webnotes.conn.sql(query, args, as_dict=1)

	# add All Products link
	total_count = sum((r.get('items') or 0 for r in result))
	result = [{'items': total_count, 'item_group': 'All Products'}] + (result or [])
	
	return result
	
@webnotes.whitelist(allow_guest=True)
def get_similar_product_list(args=None):
	"""
		args = {
			'limit_start': 0,
			'limit_page_length': 5,
			'product_name': '',
			'product_group': '',
		}
	"""
	import webnotes
	
	if not args: args = webnotes.form_dict
	
	query = """\
		select name, item_name, page_name, website_image,
		description, web_short_description
		from `tabItem`
		where is_sales_item = 'Yes'
		and docstatus = 0
		and show_in_website = 1
		and name != %(product_name)s
		and item_group = %(product_group)s
		order by item_name"""
	
	from webnotes.widgets.query_builder import add_limit_to_query
	query, args = add_limit_to_query(query, args)
	
	result = webnotes.conn.sql(query, args, as_dict=1)
		
	return result