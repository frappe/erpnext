QUnit.module('hr');

QUnit.test("Test: Leave type [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// test leave type creation
		() => frappe.set_route("List", "Leave Type", "List"),
		() => frappe.new_doc("Leave Type"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("leave_type_name", "Test Leave type"),
		() => cur_frm.set_value("max_continuous_days_allowed", "5"),
		() => frappe.click_check('Is Carry Forward'),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Test Leave type", cur_frm.doc.leave_type_name,
			'leave type correctly saved'),
		() => done()
	]);
});
