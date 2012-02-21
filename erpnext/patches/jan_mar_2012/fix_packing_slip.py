def execute():
	"""
		* Change DN to PS mapper
			+ Set Ref doc should be submitted to 0
			+ Set validation logic of DN PS Table mapper record to docstatus=0
	"""
	import webnotes
	webnotes.conn.sql("""\
		UPDATE `tabDocType Mapper`
		SET ref_doc_submitted=0
		WHERE name='Delivery Note-Packing Slip'""")
	
	webnotes.conn.sql("""\
		UPDATE `tabTable Mapper Detail`
		SET validation_logic='docstatus=0'
		WHERE parent='Delivery Note-Packing Slip'
		AND docstatus=0
		AND from_table='Delivery Note'
		AND to_table='Packing Slip'""")

