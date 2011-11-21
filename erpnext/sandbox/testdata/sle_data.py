from webnotes.model.doc import Document

# Existing SLE data
#---------------------------

sle = [
	Document(
		fielddata = {
			'doctype': 'Stock Ledger Entry',
			'name': 'sle1',
			'posting_date': '2011-09-01',
			'posting_time': '12:00',
			'item_code': 'it',
			'warehouse': 'wh1',
			'actual_qty': 10,
			'incoming_rate': 100,
			'bin_aqat': 10,
			'valuation_rate': 100,
			'fcfs_stack': '',
			'stock_value': 1000,
			'is_cancelled': 'No'			
		}
	),
		Document(
		fielddata = {
			'doctype': 'Stock Ledger Entry',
			'name': 'sle2',
			'posting_date': '2011-09-01',
			'posting_time': '12:00',
			'item_code': 'it',
			'warehouse': 'wh1',
			'actual_qty': -5,
			'incoming_rate': 100,
			'bin_aqat': 5,
			'valuation_rate': 100,
			'fcfs_stack': '',
			'stock_value': 500,
			'is_cancelled': 'No'
		}
	),
	Document(
		fielddata = {
			'doctype': 'Stock Ledger Entry',
			'name': 'sle3',
			'posting_date': '2011-09-10',
			'posting_time': '15:00',
			'item_code': 'it',
			'warehouse': 'wh1',
			'actual_qty': 20,
			'incoming_rate': 200,
			'bin_aqat': 25,
			'valuation_rate': 180,
			'fcfs_stack': '',
			'stock_value': 4500,
			'is_cancelled': 'No'			
		}
	),
	Document(
		fielddata = {
			'doctype': 'Stock Ledger Entry',
			'name': 'sle4',
			'posting_date': '2011-09-15',
			'posting_time': '09:30',
			'item_code': 'it',
			'warehouse': 'wh1',
			'actual_qty': -5,
			'incoming_rate': 180,
			'bin_aqat': 20,
			'valuation_rate': 180,
			'fcfs_stack': '',
			'stock_value': 3600,
			'is_cancelled': 'No'			
		}
	)
]

bin = Document(
	fielddata = {
		'doctype': 'Bin',
		'name': 'bin01',
		'item_code': 'it',
		'warehouse': 'wh1',
		'actual_qty': 20,
	}
)
