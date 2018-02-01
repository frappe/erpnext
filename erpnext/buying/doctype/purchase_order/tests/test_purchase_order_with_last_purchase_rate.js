QUnit.module('Buying');

QUnit.test("test: purchase order with last purchase rate", function(assert) {
	assert.expect(9);
	let done = assert.async();

	frappe.run_serially([
		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{is_subcontracted: 'No'},
				{currency: 'INR'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 1},
						{"rate": 800},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					],
					[
						{"item_code": 'Test Product 1'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 1},
						{"rate": 400},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]}
			]);
		},

		() => {
			// Get item details
			assert.ok(cur_frm.doc.items[0].item_name == 'Test Product 4', "Item 1 name correct");
			assert.ok(cur_frm.doc.items[1].item_name == 'Test Product 1', "Item 2 name correct");
		},

		() => frappe.timeout(1),

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(3),

		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(1),

		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{is_subcontracted: 'No'},
				{currency: 'INR'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 1},
						{"rate": 600},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					],
					[
						{"item_code": 'Test Product 1'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 1},
						{"rate": 200},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]}
			]);
		},

		() => frappe.timeout(2),

		// Get the last purchase rate of items
		() => {
			assert.ok(cur_frm.doc.items[0].last_purchase_rate == 800, "Last purchase rate of item 1 correct");
			assert.ok(cur_frm.doc.items[1].last_purchase_rate != 0);
		},
		() => {
			assert.ok(cur_frm.doc.items[1].last_purchase_rate == 400, "Last purchase rate of item 2 correct");
			assert.ok(cur_frm.doc.items[1].last_purchase_rate != 0);
		},

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(3),

		() => frappe.tests.click_button('Close'),

		() => frappe.timeout(1),

		() => {
			assert.ok(cur_frm.doc.status == 'To Receive and Bill', "Submitted successfully");
		},

		// enable allow_last_purchase_rate
		() => {
			return frappe.tests.make('Buying Settings', [
				// values to be set
				{"disable_fetch_last_purchase_rate": 1}
			]);
		},

		() => {
			return frappe.tests.make('Purchase Order', [
				{supplier: 'Test Supplier'},
				{is_subcontracted: 'No'},
				{currency: 'INR'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 1},
						{"rate": 800},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					],
					[
						{"item_code": 'Test Product 1'},
						{"schedule_date": frappe.datetime.add_days(frappe.datetime.now_date(), 1)},
						{"expected_delivery_date": frappe.datetime.add_days(frappe.datetime.now_date(), 5)},
						{"qty": 1},
						{"rate": 400},
						{"warehouse": 'Stores - '+frappe.get_abbr(frappe.defaults.get_default("Company"))}
					]
				]}
			]);
		},

		() => {
			// Get item details
			assert.ok(cur_frm.doc.items[0].last_purchase_rate == 0);
			assert.ok(cur_frm.doc.items[1].last_purchase_rate == 0);
		},

		() => frappe.timeout(1),

		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(3),

		() => frappe.tests.click_button('Close'),
		() => frappe.timeout(1),

		// enable allow_last_purchase_rate
		() => frappe.tests.make('Buying Settings', [
			// values to be set
			{"disable_fetch_last_purchase_rate": 0}
		]),

		() => done()
	]);
});