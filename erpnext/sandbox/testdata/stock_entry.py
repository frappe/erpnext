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
			'name': 'ste'
		}
	),
	Document(
		fielddata  ={
			'doctype': 'Stock Entry Detail',
			'parenttype': 'Stock Entry',
			'parentfield' : 'mtn_details',
			'parent' : 'ste',
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
