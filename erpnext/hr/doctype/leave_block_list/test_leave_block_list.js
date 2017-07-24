QUnit.module('hr');

QUnit.test("Test: Leave block list [HR]", function (assert) {
	assert.expect(0);
	let done = assert.async();

	frappe.run_serially([
		// test leave block list creation
		() => frappe.set_route("List", "Leave Block List", "List"),
		() => frappe.new_doc("Leave Block List"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("leave_block_list_name", "Leave block list test"),
		() => cur_frm.set_value("from_date", date),
		() => cur_frm.set_value("weekly_off", "Sunday"),		// holiday list for sundays
		() => frappe.click_button('Get Weekly Off Dates'),

		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Holiday list test", cur_frm.doc.holiday_list_name,
			'name of holiday list correctly saved'),

		// check if holiday list contains correct days
		() => {
			var list = cur_frm.doc.holidays;
			var list_length = list.length;
			var i = 0;
			for ( ; i < list_length; i++)
				if (list[i].description != 'Sunday') break;
			assert.equal(list_length, i, "all holidays are sundays in holiday list");
		},

		// check if to_date is set one year from from_date
		() => {
			var date_year_later = frappe.datetime.add_days(frappe.datetime.add_months(date, 12), -1);		// date after one year
			assert.equal(date_year_later, cur_frm.doc.to_date,
				"to date set correctly");
		},
		() => done()
	]);
});