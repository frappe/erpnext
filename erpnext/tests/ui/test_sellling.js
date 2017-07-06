QUnit.module('sales');

QUnit.test("test quotation", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.tests.setup_doctype('Customer'),
		() => frappe.tests.setup_doctype('Item'),
		() => {
			return frappe.tests.make('Quotation', [
				{customer: 'Test Customer 1'},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 5}
					]
				]}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1');

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total==500);
		},
		() => done()
	]);
});


QUnit.only("test sales order", function(assert) {
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.tests.setup_doctype('Sales Taxes and Charges Template'),
		() => {
			return frappe.tests.make('Sales Order', [
				{customer: 'Test Customer 1'},
				{delivery_date: frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
				{taxes_and_charges: 'TEST In State GST'},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 5}
					]
				]},
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1');

			//get tax details
			assert.ok(cur_frm.doc.taxes[0].account_head=='CGST - '+frappe.get_abbr(frappe.defaults.get_default('Company')));
			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total==590);
		},
		() => done()
	]);
});

/*
QUnit.only("test taxes", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('', [
				{customer: 'Test Customer 1'},
				{delivery_date: frappe.datetime.add_days(frappe.defaults.get_default("year_end_date"), 1)},
				{items: [
					[
						{'item_code': 'Test Product 1'},
						{'qty': 5}
					]
				]}
			]);
		},
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.items[0].item_name=='Test Product 1');

			// calculate_taxes_and_totals
			assert.ok(cur_frm.doc.grand_total==500);
		},
		() => done()
	]);
});

*/