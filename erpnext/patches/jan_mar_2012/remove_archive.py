# TODO take backup before running this patch
def execute():
	"""
		* Restore archived data from arc tables
		* Drop arc tables
	"""
	import webnotes
	from webnotes.utils import archive
	arc_tables = webnotes.conn.sql('show tables like "arc%"')
	try:
		webnotes.conn.auto_commit_on_many_writes = 1
		for tab in arc_tables:
			tab = tab[0]
			dt = tab[3:]
			res = webnotes.conn.sql("SELECT name FROM `%s`" % tab)
			for dn in res:
				archive.archive_doc(dt, dn[0], restore=1)
	except Exception, e:
		raise e
	else:
		webnotes.conn.commit()
		for tab in arc_tables:
			webnotes.conn.sql("DROP TABLE `%s`" % tab[0])
		webnotes.conn.begin()
