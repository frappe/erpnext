# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.conn.sql("""update tabDocPerm set `write`=1 where
		parent='Report'
		and role in ('Administrator', 'Report Manager', 'System Manager')""")