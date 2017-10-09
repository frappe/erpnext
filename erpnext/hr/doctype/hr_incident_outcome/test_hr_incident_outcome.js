/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: HR Incident Outcome", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		() => frappe.set_route("List", "HR Incident Outcome", "List"),
		() => frappe.new_doc("HR Incident Outcome"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("Outcome", "Test HR Incident Outcome"),
		() => cur_frm.set_value("Description", "Test description"),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test HR Incident Outcome", cur_frm.doc.outcome,
			'name of HR Incident Outcome correctly saved'),
		() => done()
	]);

});
