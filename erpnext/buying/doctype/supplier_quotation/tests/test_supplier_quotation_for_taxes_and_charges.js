QUnit.module('Buying');

QUnit.test("test: supplier quotation with taxes and charges", function(assert) {
	assert.expect(3);
	let done = assert.async();
	let supplier_quotation_name;

	frappe.run_serially([
		() => {
			return frappe.tests.make('Supplier Quotation', [
				{supplier: 'Test Supplier'},
				{items: [
					[
						{"item_code": 'Test Product 4'},
						{"qty": 5},
						{"rate": 100},
						{"warehouse": 'Stores - WP'},
					]
				]},
			]);
		},
		() => {supplier_quotation_name = cur_frm.doc.name;},
		() => frappe.set_route('Form', 'Purchase Taxes and Charges Template', 'New Purchase Taxes and Charges Template'),
		() => frappe.timeout(1),
		() => {
			return frappe.tests.set_form_values(cur_frm, [
				{title:'TEST In State GST'},
				{taxes: [
					[
						{"charge_type": 'On Net Total'},
						{"account_head": 'CGST - WP'}
					],
					[
						{"charge_type": 'On Net Total'},
						{"account_head": 'SGST - WP'}
					]
				]},
			]);
		},
		() => cur_frm.save(),
		() => frappe.set_route('Form', 'Supplier Quotation', supplier_quotation_name),
		() => frappe.timeout(1),
		() => {
			return frappe.tests.set_form_values(cur_frm, [
				{taxes_and_charges:'TEST In State GST'}
			]);
		},

		() => {
			assert.ok(cur_frm.doc.taxes[0].account_head=='CGST - '+frappe.get_abbr(frappe.defaults.get_default('Company')), " Account Head abbr correct");
			assert.ok(cur_frm.doc.total_taxes_and_charges == 45, "Taxes and charges correct");
			assert.ok(cur_frm.doc.grand_total == 545, "Grand total correct");
		},

		() => cur_frm.save(),
		() => frappe.timeout(0.3),
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});