QUnit.module('hr');

QUnit.test("Test: Branch [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// test branch creation
		() => frappe.set_route("List", "Branch", "List"),
		() => frappe.new_doc("Branch"),
		() => frappe.timeout(1),
		() => frappe.click_link('Edit in full page'),
		() => cur_frm.set_value("branch", "Test Branch"),

		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Branch", cur_frm.doc.branch,
			'name of branch correctly saved'),
		() => done()
	]);
});