def execute():
	import webnotes
	webnotes.conn.sql("""update `tabAccount` 
		set account_type = 'Chargeable' 
		where account_name in ('CENVAT Capital Goods', 'CENVAT Service Tax', 'CENVAT Service Tax Cess 1', 'CENVAT Service Tax Cess 2', 
			'P L A', 'P L A - Cess Portion', 'VAT', 'TDS (Advertisement)', 'TDS (Commission)', 'TDS (Contractor)', 'TDS (Interest)', 
			'TDS (Rent)', 'TDS (Salary)')
	""")

