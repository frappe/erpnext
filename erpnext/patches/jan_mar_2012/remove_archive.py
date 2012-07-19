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

# TODO take backup before running this patch
from __future__ import unicode_literals
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
