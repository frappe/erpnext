from webnotes.model.doc import Document

mr = [
	Document(
		fielddata = {
			'doctype': 'Stock Entry',
			'posting_date': '2011-09-01',
			'transfer_date': '2011-09-01',
			'posting_time': '12:00',
			'company': 'comp',
			'fiscal_year' : '2011-2012',
			'purpose': 'Material Receipt',
			'name': 'mr'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'mr',
			'item_code' : 'it',
			't_warehouse' : 'wh1',
			'qty' : 10,
			'transfer_qty' : 10,
			'incoming_rate': 100,
			'stock_uom': 'Nos',
			'conversion_factor': 1,
			'serial_no': 'srno1, srno2, srno3, srno4, srno5, srno6, srno7, srno8, srno9, srno10'	
		}
	)
]


mtn = [
	Document(
		fielddata = {
			'doctype': 'Stock Entry',
			'posting_date': '2011-09-01',
			'transfer_date': '2011-09-01',
			'posting_time': '13:00',
			'company': 'comp',
			'fiscal_year' : '2011-2012',
			'purpose': 'Material Transfer',
			'name': 'mtn'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'mtn',
			'item_code' : 'it',
			's_warehouse' : 'wh1',
			't_warehouse' : 'wh2',
			'qty' : 5,
			'transfer_qty' : 5,
			'incoming_rate': 100,
			'stock_uom': 'Nos',
			'conversion_factor': 1,
			'serial_no': 'srno1, srno2, srno3, srno4, srno5'	
		}
	)
]
