def execute():
	import webnotes
	from webnotes.utils import flt
	for dt in ["Sales Invoice", "Purchase Invoice"]:
		records = webnotes.conn.sql("""select name, outstanding_amount from `tab%s` 
			where docstatus = 1""" % dt)
		for r in records:
			outstanding = webnotes.conn.sql("""
				select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) from `tabGL Entry`
				where against_voucher = %s and against_voucher_type = %s 
				and ifnull(is_cancelled, 'No') = 'No'""", (r[0], dt))
			if flt(r[1]) != abs(flt(outstanding[0][0])):
				# print r, outstanding
				webnotes.conn.sql("update `tab%s` set outstanding_amount = %s where name = %s" %
					(dt, '%s', '%s'), (abs(flt(outstanding[0][0])), r[0]))