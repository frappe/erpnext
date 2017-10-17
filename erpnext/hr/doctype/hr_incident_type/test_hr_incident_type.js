/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: HR Incident Type", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		() => frappe.set_route("List", "HR Incident Type", "List"),
		() => frappe.new_doc("HR Incident Type"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("type", "Test Type"),
		() => cur_frm.set_value("description", "Test Type description"),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Type", cur_frm.doc.department_name,
			'name of Type correctly saved'),
		() => done()
	]);

});
