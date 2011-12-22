import webnotes

def execute():
	companies_list = webnotes.conn.sql("SELECT company_name FROM `tabCompany`", as_list=1)
	for company in companies_list:
		if company and company[0]:
			edigest = Document('Email Digest', "Default Weekly Digest - " + company[0])
			if edigest:
				edigest.income_year_to_date = 1
				edigest.save()
