import webnotes

def execute():
	create_fiscal_years()
	
	doctypes = webnotes.conn.sql_list("""select parent from tabDocField
		where (fieldtype="Link" and options='Fiscal Year')
		or (fieldtype="Select" and options='link:Fiscal Year')""")
		
	for dt in doctypes:
		date_fields = webnotes.conn.sql_list("""select fieldname from tabDocField
			where parent=%s and fieldtype='Date'""", dt)
		
		date_field = get_date_field(date_fields, dt)

		if not date_field:
			print dt, date_field
		else:
			webnotes.conn.sql("""update `tab%s` set fiscal_year = 
				if(%s<='2013-06-30', '2012-2013', '2013-2014')""" % (dt, date_field))
			
def create_fiscal_years():
	fiscal_years = {
		"2012-2013": ["2012-07-01", "2013-06-30"],
		"2013-2014": ["2013-07-01", "2014-06-30"]
	}
	
	for d in fiscal_years:
		webnotes.bean({
			"doctype": "Fiscal Year",
			"year": d,
			"year_start_date": fiscal_years[d][0],
			"is_fiscal_year_closed": "No"
		}).insert()
	
		
def get_date_field(date_fields, dt):
	date_field = None
	if date_fields:
		if "posting_date" in date_fields:
			date_field = "posting_date"
		elif "transaction_date" in date_fields:
			date_field = 'transaction_date'
		else:
			date_field = date_fields[0]
			# print dt, date_fields
			
	return date_field
		