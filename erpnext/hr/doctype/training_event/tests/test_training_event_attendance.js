QUnit.module('hr');

QUnit.test("test: Training Event", function (assert) {
	// number of asserts
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// insert a new Training Event
		() => frappe.set_route("List", "Training Event", "List"),
		() => frappe.new_doc("Training Event"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("event_name", "Test Event " + frappe.utils.get_random(10)),
		() => cur_frm.set_value("start_time", "2017-07-26, 2:00 pm PDT"),
		() => cur_frm.set_value("end_time", "2017-07-26, 2:30 pm PDT"),
		() => cur_frm.set_value("introduction", "This is a test report"),
		() => cur_frm.set_value("location", "Fake office"),
		() => frappe.click_button('Add Row'),
		() => frappe.db.get_value('Employee', {'employee_name':'Test Employee 1'}, 'name'),
		(r) => {
			console.log(r);
			return cur_frm.fields_dict.employees.grid.grid_rows[0].doc.employee = r.message.name;
		},
		() => {
			return cur_frm.fields_dict.employees.grid.grid_rows[0].doc.attendance = "Optional";
		},
		() => frappe.click_button('Save'),
		() => frappe.timeout(2),
		() => frappe.click_button('Submit'),
		() => frappe.timeout(2),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(1),
		() => {
			assert.equal(cur_frm.doc.docstatus, 1);
		},
		() => done()
	]);

});