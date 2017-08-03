QUnit.module('hr');

QUnit.test("Test: Attendance [HR]", function (assert) {
	assert.expect(4);
	let done = assert.async();

	frappe.run_serially([
		// test attendance creation for one employee
		() => frappe.set_route("List", "Attendance", "List"),
		() => frappe.timeout(0.5),
		() => frappe.new_doc("Attendance"),
		() => frappe.timeout(1),
		() => assert.equal("Attendance", cur_frm.doctype,
			"Form for new Attendance opened successfully."),
		// set values in form
		() => cur_frm.set_value("company", "Test Company"),
		() => frappe.db.get_value('Employee', {'employee_name':'Test Employee 1'}, 'name'),
		(employee) => cur_frm.set_value("employee", employee.message.name),
		() => cur_frm.save(),
		() => frappe.timeout(1),
		// check docstatus of attendance before submit [Draft]
		() => assert.equal("0", cur_frm.doc.docstatus,
			"attendance is currently drafted"),
		// check docstatus of attendance after submit [Present]
		() => cur_frm.savesubmit(),
		() => frappe.timeout(0.5),
		() => frappe.click_button('Yes'),
		() => assert.equal("1", cur_frm.doc.docstatus,
			"attendance is saved after submit"),
		// check if auto filled date is present day
		() => assert.equal(frappe.datetime.nowdate(), cur_frm.doc.attendance_date,
			"attendance for Present day is marked"),
		() => done()
	]);
});