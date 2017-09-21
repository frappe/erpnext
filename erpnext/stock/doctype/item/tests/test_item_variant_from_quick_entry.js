QUnit.module('stock');
QUnit.test('Test: Item variant Creation from Quick Entry', function(assert){
	assert.expect(4);
	let done = assert.async();
	let drill_cost  = 800;
	let is_stock_item = 1;
	let has_variants = 1;
	frappe.run_serially([
		// test item template creation
		() => frappe.set_route("List", "Item"),
		() => frappe.timeout(0.5),

		// Create a Drill item template
		() => frappe.tests.make(
			"Item", [
				{item_code: "Drill"},
				{item_group: "Products"},
				{is_stock_item: is_stock_item},
				{standard_rate: drill_cost},
				{has_variants: has_variants},
				{variant_based_on: "Item Attribute"},
				{attributes: [
					[
						{'attribute': 'Colour'}
					],
					[
						{
							'attribute': 'Flute Diameter',
							'numeric_values': 1
						}
					]
				]}
			]
		),
		() => {
			assert.ok(cur_frm.doc.has_variants==1, "Has variant checked");
			assert.ok(cur_frm.doc.attributes[0].attribute=='Colour',
				"Attribute added successfully");
			assert.ok(cur_frm.doc.variant_based_on=='Item Attribute',
				"variant_based_on set correctly");
		},
		() => frappe.timeout(1),
		
		// create Item variant
		() => frappe.set_route('List', 'Item'),
		() => frappe.new_doc("Item"),
		() => frappe.timeout(0.5),
		() => cur_dialog.fields_dict.create_variant.$input.click(),
		() => cur_dialog.set_value('item_template',"Drill"),
		() => cur_dialog.fields_dict["item_template"].df.onchange(),
		() => frappe.timeout(0.8),
		() => cur_dialog.set_value('item_group',"Products"),
		
		// set attribute value
		() => cur_dialog.fields_dict.attribute_html.$wrapper.find('[data-fieldname=Colour]').val("Red"),
		() => cur_dialog.fields_dict.attribute_html.$wrapper.find('[data-fieldname=Colour]').trigger("awesomplete-close"),
		() => cur_dialog.fields_dict.attribute_html.$wrapper.find('[data-fieldname="Flute Diameter"]').val("12"),
		() => cur_dialog.fields_dict.attribute_html.$wrapper.find('[data-fieldname="Flute Diameter"]').trigger("change"),
		() => frappe.timeout(0.5),
		() => cur_dialog.get_primary_btn().click(),
		() => frappe.timeout(1),

		// check in item list if new item variant is created
		() => frappe.set_route("List", "Item", "List"),
		() => frappe.click_button('Refresh'),
		() => frappe.timeout(0.5),
		() => assert.equal(cur_list.data[0].name, 'Drill-RED-12',
			"Added Item variant is visible in item list."),
		() => done()
	]);
});
