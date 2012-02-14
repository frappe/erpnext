def execute():	
	from webnotes.modules import reload_doc
	reload_doc('website', 'doctype', 'website_settings')
	reload_doc('website', 'doctype', 'product_settings')
	