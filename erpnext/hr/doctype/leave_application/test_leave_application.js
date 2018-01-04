QUnit.module('hr');

QUnit.test("Test: Leave application [HR]", function (assert) {
	assert.expect(4);
	let done = assert.async();
	let today_date = frappe.datetime.nowdate();
	let leave_date = frappe.datetime.add_days(today_date, 1);	// leave for tomorrow

	frappe.run_serially([
		// test creating leave application
		() => frappe.db.get_value('Employee', {'employee_name':'Test Employee 1'}, 'name'),
		(employee) => {
			return frappe.tests.make('Leave Application', [
				{leave_type: "Test Leave type"},
				{from_date: leave_date},	// for today
				{to_date: leave_date},
				{half_day: 1},
				{employee: employee.message.name},
				{leave_approver: "Administrator"},
				{follow_via_email: 0}
			]);
		},
		() => frappe.timeout(1),
		// check calculated total leave days
		() => assert.ok(!cur_frm.doc.docstatus,
			"leave application not submitted with status as open"),
		() => cur_frm.set_value("status", "Approved"),	// approve the application [as administrator]
		() => frappe.timeout(0.5),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),
		() => assert.ok(cur_frm.doc.docstatus,
			"leave application submitted after approval"),
		// check auto filled posting date [today]
		() => assert.equal(today_date, cur_frm.doc.posting_date,
			"posting date correctly set"),
		() => frappe.set_route("List", "Leave Application", "List"),
		() => frappe.timeout(1),
		// check approved application in list
		() => assert.deepEqual(["Test Employee 1", "Approved"], [cur_list.data[0].employee_name, cur_list.data[0].status],
			"leave for correct employee is approved"),
		() => done()
	]);
});