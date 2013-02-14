test_records = [[{
		"doctype":"Leave Block List",
		"leave_block_list_name": "_Test Leave Block List",
		"year": "_Test Fiscal Year 2013",
		"company": "_Test Company"
	}, {
		"doctype": "Leave Block List Date",
		"parent": "_Test Leave Block List",
		"parenttype": "Leave Block List",
		"parentfield": "leave_block_list_dates",
		"block_date": "2013-01-02",
		"reason": "First work day"
	}, {
		"doctype": "Leave Block List Allow",
		"parent": "_Test Leave Block List",
		"parenttype": "Leave Block List",
		"parentfield": "leave_block_list_allowed",
		"allow_user": "test1@example.com",
		}
	]]