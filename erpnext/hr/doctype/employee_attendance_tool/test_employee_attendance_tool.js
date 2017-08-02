QUnit.module('hr');

QUnit.test("Test: Employee attendance tool [HR]", function (assert) {
	assert.expect(3);
	let done = assert.async();
	let today_date = frappe.datetime.nowdate();
	let date_of_attendance = frappe.datetime.add_days(today_date, -1);	// previous day

	frappe.run_serially([
		// create employee
		() => {
			return frappe.tests.make('Employee', [
				{salutation: "Mr"},
				{employee_name: "Test Employee 2"},
				{company: "Test Company"},
				{date_of_joining: frappe.datetime.add_months(today_date, -2)},	// joined 2 month from now
				{date_of_birth: frappe.datetime.add_months(today_date, -240)},	// age is 20 years
				{employment_type: "Test Employment type"},
				{holiday_list: "Test Holiday list"},
				{branch: "Test Branch"},
				{department: "Test Department"},
				{designation: "Test Designation"}
			]);
		},
		() => frappe.set_route("Form", "Employee Attendance Tool"),
		() => frappe.timeout(0.5),
		() => assert.equal("Employee Attendance Tool", cur_frm.doctype,
			"Form for Employee Attendance Tool opened successfully."),
		// set values in form
		() => cur_frm.set_value("date", date_of_attendance),
		() => cur_frm.set_value("branch", "Test Branch"),
		() => cur_frm.set_value("department", "Test Department"),
		() => cur_frm.set_value("company", "Test Company"),
		() => frappe.timeout(1),
		() => frappe.click_button('Check all'),
		() => frappe.click_button('Mark Present'),
		// check if attendance is marked
		() => frappe.set_route("List", "Attendance", "List"),
		() => frappe.timeout(1),
		() => {
			assert.deepEqual(["Test Employee 2", "Test Employee 1"], [cur_list.data[0].employee_name, cur_list.data[1].employee_name],
				"marked attendance correctly saved for both employee");
			let marked_attendance = cur_list.data.filter(d => d.attendance_date == date_of_attendance);
			assert.equal(marked_attendance.length, 2,
				'both the attendance are marked for correct date');
		},
		() => done()
	]);
});