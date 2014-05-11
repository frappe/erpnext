# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
	# delete wrong gle entries created due to a bug in make_gl_entries of Account Controller
	# when using payment reconciliation
	res = webnotes.conn.sql_list("""select distinct gl1.voucher_no
		from `tabGL Entry` gl1, `tabGL Entry` gl2
		where
		date(gl1.modified) >= "2013-03-11"
		and date(gl1.modified) = date(gl2.modified)
		and gl1.voucher_no = gl2.voucher_no
		and gl1.voucher_type = "Journal Voucher"
		and gl1.voucher_type = gl2.voucher_type
		and gl1.posting_date = gl2.posting_date
		and gl1.account = gl2.account
		and ifnull(gl1.is_cancelled, 'No') = 'No' and ifnull(gl2.is_cancelled, 'No') = 'No' 
		and ifnull(gl1.against_voucher, '') = ifnull(gl2.against_voucher, '')
		and ifnull(gl1.against_voucher_type, '') = ifnull(gl2.against_voucher_type, '')
		and gl1.remarks = gl2.remarks
		and ifnull(gl1.debit, 0) = ifnull(gl2.credit, 0)
		and ifnull(gl1.credit, 0) = ifnull(gl2.debit, 0)
		and gl1.name > gl2.name""")
	
	for r in res:
		webnotes.conn.sql("""update `tabGL Entry` set `is_cancelled`='Yes'
			where voucher_type='Journal Voucher' and voucher_no=%s""", r)
		jv = webnotes.bean("Journal Voucher", r)
		jv.run_method("make_gl_entries")
	