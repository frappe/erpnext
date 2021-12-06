QUnit.test("test sales order", function(assert) {
	assert.expect(4);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Product Bundle', [
				{new_item_code: 'Computer'},
				{items: [
					[
						{item_code:'CPU'},
						{qty:1}
					],
					[
						{item_code:'Screen'},
						{qty:1}
					],
					[
						{item_code:'Keyboard'},
						{qty:1}
					]
				]},
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_code=='CPU', "Item Code correct");
			assert.ok(cur_frm.doc.items[1].item_code=='Screen', "Item Code correct");
			assert.ok(cur_frm.doc.items[2].item_code=='Keyboard', "Item Code correct");
			assert.ok(cur_frm.doc.new_item_code == "Computer", "Parent Item correct");
		},
		() => frappe.timeout(0.3),
		() => done()
	]);
});
