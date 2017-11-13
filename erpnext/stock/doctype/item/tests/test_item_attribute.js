QUnit.module('stock');
QUnit.test('Test: Item Attribute', function(assert){
	assert.expect(3);
	let done = assert.async();
	let from_range = 10;
	let to_range = 20;
	let increment = 2;
	frappe.run_serially([
		// test item attribute creation
		() => frappe.set_route("List", "Item Attribute"),
		() => frappe.timeout(0.5),
		() => frappe.tests.make(
			'Item Attribute', [
				{attribute_name: 'Rotation'},
				{item_attribute_values: [
					[
						{'attribute_value': 'Right Hand'},
						{'abbr': 'RH'},
					],
					[
						{'attribute_value': 'Left Hand'},
						{'abbr': 'LH'},
					]
				]},
			]
		),

		// Get attribute details
		() => {
			assert.ok(cur_frm.doc.attribute_name=="Rotation", "Attribute Name correct")
			assert.ok(cur_frm.doc.item_attribute_values[0].attribute_value=='Right Hand',
				"Attribute value correct");
			assert.ok(cur_frm.doc.item_attribute_values[0].abbr=='RH',
				"Abbrevation correct");
		},

		// test item attribute with numeric values
		() => frappe.tests.make(
			'Item Attribute', [
				{attribute_name: 'Flute Diameter'},
				{numeric_values: 1},
				{from_range: from_range},
				{to_range: to_range},
				{increment: increment},
			]
		),
		() => done()
	]);
});