QUnit.module('hr');

QUnit.test("Test: Employee attendance tool [HR]", function (assert) {
	assert.expect(3);
	let done = assert.async();
	let attendance_date = frappe.datetime.add_days(frappe.datetime.nowdate(), -1);	// previous day

	frappe.run_serially([
		() => frappe.set_route("Form", "Employee Attendance Tool"),
		() => frappe.timeout(0.5),
		() => assert.equal("Employee Attendance Tool", cur_frm.doctype,
			"Form for Employee Attendance Tool opened successfully."),
 		// set values in form
		() => cur_frm.set_value("date", attendance_date),
		() => cur_frm.set_value("branch", "Test Branch"),
		() => cur_frm.set_value("department", "Test Department"),
		() => cur_frm.set_value("company", "Test Company"),
		() => frappe.timeout(0.5),
		() => frappe.click_check('Test Employee'),
		() => frappe.tests.click_button('Mark Present'),
		// check if attendance is marked
		() => frappe.set_route("List", "Attendance", "List"),
		() => frappe.timeout(1),
		() => {
			assert.equal("Test Employee", cur_list.data[0].employee_name,
				"attendance marked correctly saved");
			assert.equal(attendance_date, cur_list.data[0].attendance_date,
				"attendance date is set correctly");
		},
		() => done()
	]);
});