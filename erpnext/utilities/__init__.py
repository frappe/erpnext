import webnotes

@webnotes.whitelist()
def get_report_list(arg=None):
	"""return list of reports for the given module module"""	
	webnotes.response['values'] = webnotes.conn.sql("""select 
		distinct criteria_name, doc_type, parent_doc_type
		from `tabSearch Criteria` 
		where module='%(module)s' 
		and docstatus in (0, NULL) 
		order by criteria_name 
		limit %(limit_start)s, %(limit_page_length)s""" % webnotes.form_dict, as_dict=True)