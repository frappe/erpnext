QUnit.module('Sales Taxes and Charges Template');

QUnit.test("test sales taxes and charges template", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Sales Taxes and Charges Template', [
				{title: "TEST In State GST"},
				{taxes:[
					[
						{charge_type:"On Net Total"},
						{account_head:"CGST - "+frappe.get_abbr(frappe.defaults.get_default("Company")) }
					],
					[
						{charge_type:"On Net Total"},
						{account_head:"SGST - "+frappe.get_abbr(frappe.defaults.get_default("Company")) }
					]
				]}
			]);
		},
		() => {assert.ok(cur_frm.doc.title=='TEST In State GST');},
		() => done()
	]);
});

