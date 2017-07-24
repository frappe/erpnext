QUnit.module('hr');

QUnit.test("Test: Leave block list [HR]", function (assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// test leave block list creation
		() => frappe.set_route("List", "Leave Block List", "List"),
		() => frappe.new_doc("Leave Block List"),
		() => frappe.timeout(1),
		() => cur_frm.set_value("leave_block_list_name", "Leave block list test"),
		
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => assert.equal("Leave block list test", cur_frm.doc.leave_block_list_name,
			'name of blocked leave list correctly saved'),
		() => done()
	]);
});