/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: HR Incident Body Part", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		() => frappe.set_route("List", "HR Incident Body Part", "List"),
		() => frappe.new_doc("HR Incident Body Part"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("body_part", "Test body part"),
		() => cur_frm.set_value("description", "Test body part description"),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test body part", cur_frm.doc.department_name,
			'name of body part correctly saved'),
		() => done()
	]);

});
