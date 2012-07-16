import webnotes
def execute():
	webnotes.conn.commit()
	
	from webnotes.install_lib.install import Installer
	Installer(None, None).create_auth_table()

	webnotes.conn.begin()
	
	for user, password in webnotes.conn.sql("""select name, password from tabProfile"""):
		webnotes.conn.sql("""insert into __Auth (user, `password`) values (%s, %s)""",
			(user, password))
