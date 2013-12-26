# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

def execute():
	import webnotes
	from webnotes.utils import flt
	records = webnotes.conn.sql("""
		select against_voucher_type, against_voucher, 
			sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) as outstanding from `tabGL Entry`
		where ifnull(is_cancelled, 'No') = 'No' 
		and against_voucher_type in ("Sales Invoice", "Purchase Invoice")
		and ifnull(against_voucher, '') != ''
		group by against_voucher_type, against_voucher""", as_dict=1)
	for r in records:
		outstanding = webnotes.conn.sql("""select name, outstanding_amount from `tab%s` 
			where name = %s and docstatus = 1""" % 
			(r["against_voucher_type"], '%s'), (r["against_voucher"]))
			
		if outstanding and abs(flt(r["outstanding"])) != flt(outstanding[0][1]):
			if ((r["against_voucher_type"]=='Sales Invoice' and flt(r["outstanding"]) >= 0) \
				or (r["against_voucher_type"]=="Purchase Invoice" and flt(["outstanding"]) <= 0)):
				webnotes.conn.set_value(r["against_voucher_type"], r["against_voucher"], 
					"outstanding_amount", abs(flt(r["outstanding"])))		