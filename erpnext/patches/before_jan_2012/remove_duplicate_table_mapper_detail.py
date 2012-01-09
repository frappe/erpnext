"""
	Removes duplicate entries created in 
"""
import webnotes
def execute():
	res = webnotes.conn.sql("""\
		SELECT a.name
		FROM
			`tabTable Mapper Detail` a,
			`tabTable Mapper Detail` b
		WHERE
			a.parent = b.parent AND
			a.from_table = b.from_table AND
			a.to_table = b.to_table AND
			a.from_field = b.from_field AND
			a.to_field = b.to_field AND
			a.name < b.name""")
	if res and len(res)>0:
		name_string = ", ".join(["'" + str(r[0]) + "'" for r in res])
		res = webnotes.conn.sql("""\
			DELETE FROM `tabTable Mapper Detail`
			WHERE name IN (%s)""" % name_string)
