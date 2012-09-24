# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
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

	singles = webnotes.conn.sql("""SELECT doctype, value FROM `tabSingles`
		WHERE field='file_list'""")
	for doctype, file_list in singles:
		if file_list and "/" in file_list:
			webnotes.conn.sql("""UPDATE `tabSingles` SET value='%s'
				WHERE doctype='%s' AND field='file_list'"""
				% (file_list.replace('/', '-'), doctype))

