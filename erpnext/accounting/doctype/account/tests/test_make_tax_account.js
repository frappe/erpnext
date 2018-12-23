QUnit.module('accounts');
QUnit.test("test account", assert => {
	assert.expect(3);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('Tree', 'Account'),
		() => frappe.click_button('Expand All'),
		() => frappe.click_link('Duties and Taxes - '+ frappe.get_abbr(frappe.defaults.get_default("Company"))),
		() => {
			if($('a:contains("CGST"):visible').length == 0){
				return frappe.map_tax.make('CGST', 9);
			}
		},
		() => {
			if($('a:contains("SGST"):visible').length == 0){
				return frappe.map_tax.make('SGST', 9);
			}
		},
		() => {
			if($('a:contains("IGST"):visible').length == 0){
				return frappe.map_tax.make('IGST', 18);
			}
		},
		() => {
			assert.ok($('a:contains("CGST"):visible').length!=0, "CGST Checked");
			assert.ok($('a:contains("SGST"):visible').length!=0, "SGST Checked");
			assert.ok($('a:contains("IGST"):visible').length!=0, "IGST Checked");
		},
		() => done()
	]);
});


frappe.map_tax = {
	make:function(text,rate){
		return frappe.run_serially([
			() => frappe.click_button('Add Child'),
			() => frappe.timeout(0.2),
			() => cur_dialog.set_value('account_name',text),
			() => cur_dialog.set_value('account_type','Tax'),
			() => cur_dialog.set_value('tax_rate',rate),
			() => cur_dialog.set_value('account_currency','INR'),
			() => frappe.click_button('Create New'),
		]);
	}
};
