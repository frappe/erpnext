QUnit.module('hr');

QUnit.test("Test: Leave application [HR]", function (assert) {
	assert.expect(??????????????);
	let done = assert.async();
	let today_date = frappe.datetime.nowdate();

	frappe.run_serially([
		// test creating leave application
		() => frappe.set_route("List", "Leave Application", "List"),
		() => frappe.new_doc("Leave Application"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("leave_type", "Test Leave type"),
		() => cur_frm.set_value("from_date", today_date),	// for today
		() => cur_frm.set_value("to_date", today_date),
		() => frappe.click_check('Half Day'),
		() => cur_frm.set_value("description", "This leave is just for testing, will take more later"),
		() => frappe.db.get_value('Employee', {'employee_name':'Test Employee 1'}, 'name'),
		(employee) => cur_frm.set_value("employee", employee.message.name),
		() => cur_frm.set_value("leave_approver", "Administrator"),
		() => frappe.click_check('Follow via Email'),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		// check total leave days
		() => assert.equal("0.5", cur_frm.doc.total_leave_days,
			"leave application for half day"),
		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),
		() => assert.equal("Only Leave Applications with status 'Approved' and 'Rejected' can be submitted", cur_dialog.body.innerText,
			"application not submitted with status as open"),
		() => frappe.click_button('Close'),
		() => frappe.timeout(0.5),
		() => cur_frm.set_value("status", "Approved"),	// approve the application [as administrator]
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => cur_frm.savesubmit(),
		() => frappe.timeout(1),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),
		// check auto filled posting date
		() => assert.equal(today_date, cur_frm.doc.posting_date,
			"posting date correctly set"),

			'confirmation message for submit leave application shown'),
		
		// check for total leaves
		() => assert.equal(cur_frm.doc.carry_forwarded_leaves + 2, cur_frm.doc.total_leaves_allocated,
			"total leave calculation is correctly set"),
		() => done()
	]);
});