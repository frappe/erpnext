# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	webnotes.conn.sql("""update tabDocPerm set permlevel=0 where permlevel is null""")
	webnotes.conn.sql("""update tabDocPerm set `create`=0, `submit`=0, `cancel`=0,
		`amend`=0, `match`='' where permlevel>0""")
	webnotes.delete_doc("Permission Control")