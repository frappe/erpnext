/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Restaurant Menu", function (assert) {
	let done = assert.async();

	let items =  {
		"Food Item 1": [
			{item_code: "Food Item 1"},
			{item_group: "Products"},
			{is_stock_item: 1},
		],
		"Food Item 2": [
			{item_code: "Food Item 2"},
			{item_group: "Products"},
			{is_stock_item: 1},
		],
		"Food Item 3": [
			{item_code: "Food Item 3"},
			{item_group: "Products"},
			{is_stock_item: 1},
		]
	};


	// number of asserts
	assert.expect(0);

	frappe.run_serially([
		// insert a new Restaurant Menu
		() => frappe.tests.setup_doctype('Item', items),
		() => {
			return frappe.tests.make("Restaurant Menu", [
				{__newname: 'Restaurant Menu 1'},
				{restaurant: "Test Restaurant 1"},
				{items: [
					[
						{"item": "Food Item 1"},
						{"rate": 100}
					],
					[
						{"item": "Food Item 2"},
						{"rate": 90}
					],
					[
						{"item": "Food Item 3"},
						{"rate": 80}
					]
				]}
			]);
		},
		() => frappe.timeout(2),
		() => {
			return frappe.tests.make("Restaurant Menu", [
				{__newname: 'Restaurant Menu 2'},
				{restaurant: "Test Restaurant 2"},
				{items: [
					[
						{"item": "Food Item 1"},
						{"rate": 105}
					],
					[
						{"item": "Food Item 3"},
						{"rate": 85}
					]
				]}
			]);
		},
		() => frappe.timeout(2),
		() => frappe.set_route('Form', 'Restaurant', 'Test Restaurant 1'),
		() => cur_frm.set_value('active_menu', 'Restaurant Menu 1'),
		() => cur_frm.save(),
		() => done()
	]);

});
