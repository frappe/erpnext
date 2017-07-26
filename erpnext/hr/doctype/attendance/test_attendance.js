QUnit.module('hr');

//not added path in tests.txt yet

QUnit.test("Test: Attendance [HR]", function (assert) {
	assert.expect(0);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route("List", "Attendance", "List"),
		() => frappe.timeout(0.5),
		() => frappe.new_doc("Attendance"),
		() => frappe.timeout(1),
		() => assert.equal("Attendance", cur_frm.doctype,
			"Form for new Attendance opened successfully."),
 		// set values in form
		() => cur_frm.set_value("company", "Company test"),
		() => 
		() => frappe.click_check('Employee test'),
		() => frappe.tests.click_button('Mark Present'),
		// check if attendance is marked
		() => frappe.set_route("List", "Attendance", "List"),
		() => frappe.timeout(1),
		() => {
			assert.equal("Present", cur_list.data[0].status,
				"attendance status correctly saved");
			assert.equal(frappe.datetime.nowdate(), cur_list.data[0].attendance_date,
				"attendance date is set correctly");
		}
		() => done()
	]);
});