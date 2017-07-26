QUnit.module('hr');

QUnit.test("Test: Employment type [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// test employment type creation
		() => frappe.set_route("List", "Employment Type", "List"),
		() => frappe.new_doc("Employment Type"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("employee_type_name", "Test Employment type"),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Employment type", cur_frm.doc.employee_type_name,
			'name of employment type correctly saved'),
		() => done()
	]);
});