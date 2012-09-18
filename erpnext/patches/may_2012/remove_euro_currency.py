from __future__ import unicode_literals
def execute():
	"""
		* Replace EURO with EUR
		* Delete EURO from tabCurrency
	"""
	import webnotes
	tables = webnotes.conn.sql("show tables")
	for (tab,) in tables:
		desc = webnotes.conn.sql("desc `%s`" % tab, as_dict=1)
		for d in desc:
			if "currency" in d.get('Field'):
				field = d.get('Field')
				webnotes.conn.sql("""\
					update `%s` set `%s`='EUR'
					where `%s`='EURO'""" % (tab, field, field))
	webnotes.conn.sql("update `tabSingles` set value='EUR' where value='EURO'")
	webnotes.conn.sql("delete from `tabCurrency` where name='EURO'")