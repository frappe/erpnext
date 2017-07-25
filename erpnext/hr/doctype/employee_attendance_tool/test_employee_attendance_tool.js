QUnit.module('hr');

//not added path in tests.txt yet

QUnit.test("Test: Employee attendance tool [HR]", function (assert) {
	assert.expect(0);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route("Form", "Employee Attendance Tool"),
		() => frappe.timeout(0..5),
		() => assert.equal("Employee Attendance Tool", cur_frm.doctype,
			"Form for Employee Attendance Tool opened successfully."),
 		// set values in form
		() => cur_frm.set_value("date", frappe.datetime.nowdate()),
		() => cur_frm.set_value("branch", "Branch test"),
		() => cur_frm.set_value("department", "Department test"),
		() => cur_frm.set_value("company", "Company test"),
		() => frappe.click_check('Employee test'),
		() => frappe.tests.click_button('Mark Present'),
		// check if attendance is marked
		() => frappe.set_route("List", "Attendance", "List"),
		() => frappe.timeout(1),
		() => {
			assert.
		}
		() => done()
	]);
});