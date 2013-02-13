test_records = [[{
		"doctype":"Holiday Block List",
		"holiday_block_list_name": "_Test Holiday Block List",
		"year": "_Test Fiscal Year 2013",
		"company": "_Test Company"
	}, {
		"doctype": "Holiday Block List Date",
		"parent": "_Test Holiday Block List",
		"parenttype": "Holiday Block List",
		"parentfield": "holiday_block_list_dates",
		"block_date": "2013-01-02",
		"reason": "First work day"
	}, {
		"doctype": "Holiday Block List Allow",
		"parent": "_Test Holiday Block List",
		"parenttype": "Holiday Block List",
		"parentfield": "holiday_block_list_allowed",
		"allow_user": "test1@example.com",
		}
	]]