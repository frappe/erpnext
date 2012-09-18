from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.utils import flt
	wrong_plist = webnotes.conn.sql("""
	    select dnpi.name, dnpi.parent, dnpi.docstatus, dnpi.serial_no
		from `tabDelivery Note Packing Item` dnpi
		where ifnull(dnpi.parent, '') != '' 
		and ifnull(dnpi.parent, '') not like 'old_par%'
		and dnpi.parenttype = 'Delivery Note' 
		and not exists (
			select * from `tabDelivery Note Item` dni
			where dni.item_code = dnpi.parent_item and
			dni.name = dnpi.parent_detail_docname and
			dni.parent = dnpi.parent
		)
	""", as_dict=1)

	for d in wrong_plist:
		if d['docstatus'] == 2 and d['serial_no']:
			for s in d['serial_no'].splitlines():
				sle = webnotes.conn.sql("""
					select actual_qty, warehouse, voucher_no
					from `tabStock Ledger Entry`
					where (
						serial_no like '%s\n%%' 
						or serial_no like '%%\n%s' 
						or serial_no like '%%\n%s\n%%' 
						or serial_no = '%s'
					)
					and voucher_no != '%s'
					and ifnull(is_cancelled, 'No') = 'No'
					order by name desc
					limit 1
				"""% (s, s, s, s, d['parent']), as_dict=1)

				status = 'Not in Use'
				if sle and flt(sle[0]['actual_qty']) > 0:
					status = 'In Store'
				elif sle and flt(sle[0]['actual_qty']) < 0:
					status = 'Delivered'
				
				webnotes.conn.sql("update `tabSerial No` set status = %s, warehouse = %s where name = %s", (status, sle[0]['warehouse'], s))
				
		webnotes.conn.sql("delete from `tabDelivery Note Packing Item` where name = %s", d['name'])