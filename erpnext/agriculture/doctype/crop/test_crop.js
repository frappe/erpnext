/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Crop", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(2);

	frappe.run_serially([
		// insert a new Item
		() => frappe.tests.make('Item', [
			// values to be set
			{item_code: 'Basil Seeds'},
			{item_name: 'Basil Seeds'},
			{item_group: 'Seed'}
		]),
		// insert a new Item
		() => frappe.tests.make('Item', [
			// values to be set
			{item_code: 'Twigs'},
			{item_name: 'Twigs'},
			{item_group: 'By-product'}
		]),
		// insert a new Item
		() => frappe.tests.make('Item', [
			// values to be set
			{item_code: 'Basil Leaves'},
			{item_name: 'Basil Leaves'},
			{item_group: 'Produce'}
		]),
		// insert a new Crop
		() => frappe.tests.make('Crop', [
			// values to be set
			{title: 'Basil from seed'},
			{crop_name: 'Basil'},
			{scientific_name: 'Ocimum basilicum'},
			{materials_required: [
				[
					{item_code: 'Basil Seeds'},
					{qty: '25'},
					{uom: 'Nos'},
					{rate: '1'}
				],
				[
					{item_code: 'Urea'},
					{qty: '5'},
					{uom: 'Kg'},
					{rate: '10'}
				]
			]},
			{byproducts: [
				[
					{item_code: 'Twigs'},
					{qty: '25'},
					{uom: 'Nos'},
					{rate: '1'}
				]
			]},
			{produce: [
				[
					{item_code: 'Basil Leaves'},
					{qty: '100'},
					{uom: 'Nos'},
					{rate: '1'}
				]
			]},
			{agriculture_task: [
				[
					{task_name: "Plough the field"},
					{start_day: 1},
					{end_day: 1},
					{holiday_management: "Ignore holidays"}
				],
				[
					{task_name: "Plant the seeds"},
					{start_day: 2},
					{end_day: 3},
					{holiday_management: "Ignore holidays"}
				],
				[
					{task_name: "Water the field"},
					{start_day: 4},
					{end_day: 4},
					{holiday_management: "Ignore holidays"}
				],
				[
					{task_name: "First harvest"},
					{start_day: 8},
					{end_day: 8},
					{holiday_management: "Ignore holidays"}
				],
				[
					{task_name: "Add the fertilizer"},
					{start_day: 10},
					{end_day: 12},
					{holiday_management: "Ignore holidays"}
				],
				[
					{task_name: "Final cut"},
					{start_day: 15},
					{end_day: 15},
					{holiday_management: "Ignore holidays"}
				]
			]}
		]),
		// agriculture task list
		() => {
			assert.equal(cur_frm.doc.name, 'Basil from seed');
			assert.equal(cur_frm.doc.period, 15);
		},
		() => done()
	]);

});
