# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	return
	from webnotes.modules.import_file import import_file
	import_file("accounts", "GL Mapper", "Journal Voucher")
	import_file("accounts", "GL Mapper", "Purchase Invoice")
	import_file("accounts", "GL Mapper", "Purchase Invoice with write off")