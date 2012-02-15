import webnotes

def execute():
	"""
		* Replace / in names with - in tabFile Data
		* Change autoname in DocType File Data to FileData-.#####
		* Change FileData/ to FileData- in tabSeries
		* In each table containing file_list column, replace / with - in the data of that column
	"""
	replace_name_in_file_data()
	change_autoname_in_tabfile_data()
	change_file_data_in_tabseries()
	replace_file_list_column_entries()


def replace_name_in_file_data():
	"""
		Change / to - in tabFile Data name column entries
	"""
	files = webnotes.conn.sql("SELECT name FROM `tabFile Data`")
	for f in files:
		if "/" in f[0]:
			webnotes.conn.sql("UPDATE `tabFile Data` SET name=%s WHERE name=%s", (f[0].replace('/', '-'), f[0]))


def change_autoname_in_tabfile_data():
	"""
		Change autoname in DocType File Data to FileData-.#####
	"""
	webnotes.conn.sql("UPDATE `tabDocType` SET autoname='FileData-.#####' WHERE name='File Data'")


def change_file_data_in_tabseries():
	"""
		Change FileData/ to FileData- in tabSeries
	"""
	webnotes.conn.sql("UPDATE `tabSeries` SET name='FileData-' WHERE name='FileData/'")


def replace_file_list_column_entries():
	"""
		In each table containing file_list column, replace / with - in the data of that column
	"""
	tables = webnotes.conn.sql("SHOW TABLES")
	tab_list = []
	for tab in tables:
		columns = webnotes.conn.sql("DESC `%s`" % tab[0])
		if 'file_list' in [c[0] for c in columns]:
			tab_list.append(tab[0])

	for tab in tab_list:
		data = webnotes.conn.sql("SELECT name, file_list FROM `%s`" % tab)
		for name, file_list in data:
			if file_list and "/" in file_list:
				webnotes.conn.sql("UPDATE `%s` SET file_list='%s' WHERE name='%s'" \
					% (tab, file_list.replace('/', '-'), name))
