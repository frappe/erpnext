def execute():
	import webnotes
	webnotes.conn.sql("""update `tabAccount` 
		set account_type = 'Chargeable' 
		where name in ('CENVAT Capital Goods', 'CENVAT Service Tax', 'CENVAT Service Tax Cess 1', 'CENVAT Service Tax Cess 2')
	""")
	webnotes.conn.sql("""update tabAccount 
		set account_type = 'Tax' 
		where name in ('P L A', 'P L A - Cess Portion', 'VAT', 'TDS (Advertisement)', 'TDS (Commission)',
			'TDS (Contractor)', 'TDS (Interest)', 'TDS (Rent)', 'TDS (Salary)')
	""")
