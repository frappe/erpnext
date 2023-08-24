def get_filters_config():
	filters_config = {
		"fiscal year": {
			"label": "Fiscal Year",
			"get_field": "erpnext.accounts.utils.get_fiscal_year_filter_field",
			"valid_for_fieldtypes": ["Date", "Datetime", "DateRange"],
			"depends_on": "company",
		}
	}

	return filters_config
