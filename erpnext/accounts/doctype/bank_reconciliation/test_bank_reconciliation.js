QUnit.module('Account');

QUnit.test("test Bank Reconciliation", function(assert) {
	assert.expect(0);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('Form', 'Bank Reconciliation'),
		() => cur_frm.set_value('bank_account','Cash - FT'),
		() => frappe.click_button('Get Payment Entries'),
		() => {
			for(var i=0;i<=cur_frm.doc.payment_entries.length-1;i++){
				cur_frm.doc.payment_entries[i].clearance_date = frappe.datetime.add_days(frappe.datetime.now_date(), 2);
			}
		},
		() => {cur_frm.refresh_fields('payment_entries');},
		() => frappe.click_button('Update Clearance Date'),
		() => frappe.timeout(0.5),
		() => frappe.click_button('Close'),
		() => done()
	]);
});

