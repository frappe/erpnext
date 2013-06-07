wn.query_reports["Quotation Trends"] = {
	"filters": [
		{
			"fieldname":"period",
			"label": "Period",
			"fieldtype": "Select",
			"options": "Monthly"+NEWLINE+"Quarterly"+NEWLINE+"Half-yearly"+NEWLINE+"Yearly",
			"default": "Monthly"
		},
		{
			"fieldname":"based_on",
			"label": "Based On",
			"fieldtype": "Select",
			"options": "Item"+NEWLINE+"Item Group"+NEWLINE+"Customer"+NEWLINE+"Customer Group"+NEWLINE+"Territory"+NEWLINE+"Project",
			"default": "Item"
		},
		{
			"fieldname":"group_by",
			"label": "Group By",
			"fieldtype": "Select",
			"options": "Item"+NEWLINE+"Customer",
			"default": "Customer"
		},
		{
			"fieldname":"fiscal_year",
			"label": "Fiscal Year",
			"fieldtype": "Link",
			"options":'Fiscal Year',
			"default": "Fiscal Year"
		},
		{
			"fieldname":"company",
			"label": "Company",
			"fieldtype": "Link",
			"options": "Company",
			"default": "Company"
		},
		
	]
}