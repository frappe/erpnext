QUnit.module('Sales Order');

QUnit.test("test_sales_order_with_bypass_credit_limit_check", function(assert) {
//#PR : 10861, Author : ashish-greycube & jigneshpshah,  Email:mr.ashish.shah@gmail.com
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.new_doc('Customer'),
		() => frappe.timeout(1),
		() => frappe.quick_entry.dialog.$wrapper.find('.edit-full').click(),
		() => frappe.timeout(1),
		() => cur_frm.set_value("customer_name", "Test Customer 10"),
		() => cur_frm.add_child('credit_limits', {
			'company': cur_frm.doc.company || '_Test Company'
			'credit_limit': 1000,
			'bypass_credit_limit_check': 1}),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),

		() => frappe.new_doc('Item'),
		() => frappe.timeout(1),
		() => frappe.quick_entry.dialog.$wrapper.find('.edit-full').click(),
		() => frappe.timeout(1),
		() => cur_frm.set_value("item_code", "Test Product 10"),
		() => cur_frm.set_value("item_group", "Products"),
		() => cur_frm.set_value("standard_rate", 100),
		// save form
		() => cur_frm.save(),
		() => frappe.timeout(1),

		() => {
			return frappe.tests.make('Sales Order', [
				{customer: 'Test Customer 5'},
				{items: [
					[
						{'delivery_date': frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
						{'qty': 5},
						{'item_code': 'Test Product 10'},
					]
				]}

			]);
		},
		() => cur_frm.save(),
		() => frappe.tests.click_button('Submit'),
		() => assert.equal("Confirm", cur_dialog.title,'confirmation for submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(3),
		() => {

			assert.ok(cur_frm.doc.status=="To Deliver and Bill", "It is submited. Credit limit is NOT checked for sales order");


		},
		() => done()
	]);
});
