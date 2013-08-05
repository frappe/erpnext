# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	webnotes.conn.commit()
	
	from webnotes.install_lib.install import Installer
	Installer(None, None).create_auth_table()

	webnotes.conn.begin()
	
	for user, password in webnotes.conn.sql("""select name, password from tabProfile"""):
		if password:
			webnotes.conn.sql("""insert into __Auth (user, `password`) values (%s, %s)""",
				(user, password))
