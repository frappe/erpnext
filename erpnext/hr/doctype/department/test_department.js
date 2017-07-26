QUnit.module('hr');

QUnit.test("Test: Department [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// test department creation
		() => frappe.set_route("List", "Department", "List"),
		() => frappe.new_doc("Department"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("department_name", "Test Department"),
		() => cur_frm.set_value("leave_block_list", "Test Leave block list"),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Department", cur_frm.doc.department_name,
			'name of department correctly saved'),
		() => done()
	]);
});