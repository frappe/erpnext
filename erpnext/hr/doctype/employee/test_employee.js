QUnit.module('hr');

QUnit.test("Test: Employee [HR]", function (assert) {
	assert.expect(3);
	let done = assert.async();
	let today_date = frappe.datetime.nowdate();

	frappe.run_serially([
		// test employee creation
		() => frappe.set_route("List", "Employee", "List"),
		() => frappe.new_doc("Employee"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("employee_name", "Test Employee"),
		() => cur_frm.set_value("salutation", "Ms"),
		() => cur_frm.set_value("date_of_joining", frappe.datetime.add_months(today_date, -2)),	// joined 2 month from now
		() => cur_frm.set_value("date_of_birth", frappe.datetime.add_months(today_date, -240)),	// age is 20 years
		() => cur_frm.set_value("employment_type", "Test Employment type"),
		() => cur_frm.set_value("holiday_list", "Test Holiday list"),
		() => cur_frm.set_value("branch", "Test Branch"),
		() => cur_frm.set_value("department", "Test Department"),
		() => cur_frm.set_value("designation", "Test Designation"),
		() => frappe.click_button('Add Row'),
		() => cur_frm.fields_dict.leave_approvers.grid.grid_rows[0].doc.leave_approver="Administrator",
		// save data
		() => cur_frm.save(),
		() => frappe.timeout(1),
		// check name of employee
		() => assert.equal("Test Employee", cur_frm.doc.employee_name,
			'name of employee correctly saved'),
		// check auto filled gender according to salutation
		() => assert.equal("Female", cur_frm.doc.gender,
			'gender correctly saved as per salutation'),
		// check auto filled retirement date [60 years from DOB]
		() => assert.equal(frappe.datetime.add_months(today_date, 480), cur_frm.doc.date_of_retirement,	// 40 years from now
			'retirement date correctly saved as per date of birth'),
		() => done()
	]);
});