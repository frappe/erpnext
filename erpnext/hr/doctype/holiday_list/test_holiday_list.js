QUnit.module('hr');

QUnit.test("Test: Holiday list [HR]", function (assert) {
	assert.expect(3);
	let done = assert.async();
	let date = frappe.datetime.add_months(frappe.datetime.nowdate(), -2);		// date 2 months from now

	frappe.run_serially([
		// test holiday list creation
		() => frappe.set_route("List", "Holiday List", "List"),
		() => frappe.new_doc("Holiday List"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("holiday_list_name", "Test Holiday list"),
		() => cur_frm.set_value("from_date", date),
		() => cur_frm.set_value("weekly_off", "Sunday"),		// holiday list for sundays
		() => frappe.click_button('Get Weekly Off Dates'),

		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Holiday list", cur_frm.doc.holiday_list_name,
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
