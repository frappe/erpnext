QUnit.module('hr');

QUnit.test("Test: Designation [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// test designation creation
		() => frappe.set_route("List", "Designation", "List"),
		() => frappe.new_doc("Designation"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("designation_name", "Test Designation"),
		() => cur_frm.set_value("description", "This designation is just for testing."),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Designation", cur_frm.doc.designation_name,
			'name of designation correctly saved'),
		() => done()
	]);
});