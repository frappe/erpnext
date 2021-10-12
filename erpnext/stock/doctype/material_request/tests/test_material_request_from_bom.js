QUnit.module('manufacturing');

QUnit.test("test material request get items from BOM", function(assert) {
	assert.expect(4);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('Form', 'BOM'),
		() => frappe.timeout(3),
		() => frappe.click_button('Get Items from BOM'),
		() => frappe.timeout(3),
		() => {
			assert.ok(cur_dialog, 'dialog appeared');
		},
		() => cur_dialog.set_value('bom', 'Laptop'),
		() => cur_dialog.set_value('warehouse', 'Laptop Scrap Warehouse'),
		() => frappe.click_button('Get Items from BOM'),
		() => frappe.timeout(3),
		() => {
			assert.ok(cur_frm.doc.items[0].item_code, "First row is not empty");
			assert.ok(cur_frm.doc.items[0].item_name, "Item name is not empty");
			assert.equal(cur_frm.doc.items[0].item_name, "Laptop", cur_frm.doc.items[0].item_name);
		},
		() => cur_frm.doc.items[0].schedule_date = '2017-12-12',
		() => cur_frm.save(),
		() => done()
	]);
});
