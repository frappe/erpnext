QUnit.test("test: Activity Type", function (assert) {
	// number of asserts
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		// insert a new Activity Type
		() => frappe.set_route("List", "Activity Type", "List"),
		() => frappe.new_doc("Activity Type"),
		() => frappe.timeout(1),
		() => frappe.quick_entry.dialog.$wrapper.find('.edit-full').click(),
		() => frappe.timeout(1),
		() => cur_frm.set_value("activity_type", "Test Activity"),
		() => frappe.click_button('Save'),
		() => frappe.timeout(1),
		() => {
			assert.equal(cur_frm.doc.name,"Test Activity");
		},
		() => done()
	]);
});
