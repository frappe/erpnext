from webnotes.model.doc import Document

# Stock Reconciliation
#---------------------------

sreco = Document(
		fielddata = {
			'doctype': 'Stock Reconciliation',
			'name': 'sreco',
			'reconciliation_date': '2011-09-08',
			'reconciliation_time': '20:00',
		}
	)

# diff in both
csv_data1 = [
	['Item', 'Warehouse', 'Quantity', 'Rate'],
	['it', 'wh1', 20, 150]
]

# diff in qty, no rate
csv_data2 = [
	['Item', 'Warehouse', 'Quantity'],
	['it', 'wh1', 20]
]

# diff in rate, no qty
csv_data3 = [
	['Item', 'Warehouse', 'Rate'],
	['it', 'wh1', 200]
]

# diff in rate, same qty
csv_data4 = [
	['Item', 'Warehouse', 'Quantity', 'Rate'],
	['it', 'wh1', 5, 200]
]

# no diff
csv_data1 = [
	['Item', 'Warehouse', 'Quantity', 'Rate'],
	['it', 'wh1', 5, 100]
]
