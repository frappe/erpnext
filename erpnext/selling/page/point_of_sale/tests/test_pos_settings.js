QUnit.test("test:POS Settings", function(assert) {
	assert.expect(1);
	let done = assert.async();

	frappe.run_serially([
		() => frappe.set_route('Form', 'POS Settings'),
		() => cur_frm.set_value('use_pos_in_offline_mode', 0),
		() => frappe.timeout(0.2),
		() => cur_frm.save(),
		() => frappe.timeout(1),
		() => frappe.ui.toolbar.clear_cache(),
		() => frappe.timeout(10),
		() => assert.ok(cur_frm.doc.use_pos_in_offline_mode==0, "Enabled online"),
		() => frappe.timeout(2),
		() => done()
	]);
});