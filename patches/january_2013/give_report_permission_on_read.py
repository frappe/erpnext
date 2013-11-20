# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
def execute():
	webnotes.conn.sql("""update tabDocPerm set `report`=`read`
		where ifnull(permlevel,0)=0""")
