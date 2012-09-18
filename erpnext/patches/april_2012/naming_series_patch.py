from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.code import get_obj
	ns_list = webnotes.conn.sql("""\
		SELECT `tabDocField`.`parent`, `tabDocField`.`options`
		FROM `tabDocField`, `tabDocType`
		WHERE `tabDocField`.`fieldname` = 'naming_series'
		AND `tabDocType`.name=`tabDocField`.parent""")
	ns_obj = get_obj('Naming Series')
	for ns in ns_list:
		if ns[0] and isinstance(ns[1], basestring):			
			ns_obj.set_series_for(ns[0], ns[1].split("\n"))
