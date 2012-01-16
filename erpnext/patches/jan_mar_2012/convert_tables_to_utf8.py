import webnotes

def execute():
	sql = webnotes.conn.sql
	
	sql("commit")
	sql("set foreign_key_checks=0")
	for tab in sql("show tables"):
		sql("ALTER TABLE `%s` CONVERT TO CHARACTER SET utf8" % tab[0])

	sql("set foreign_key_checks=1")
