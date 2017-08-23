QUnit.module('Journal Entry');

QUnit.test("test journal entry", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Journal Entry', [
				{posting_date:frappe.datetime.add_days(frappe.datetime.nowdate(), 0)},
				{accounts: [
					[
						{'account':'Debtors - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
						{'party_type':'Customer'},
						{'party':'Test Customer 1'},
						{'credit_in_account_currency':1000},
						{'is_advance':'Yes'},
					],
					[
						{'account':'HDFC - '+frappe.get_abbr(frappe.defaults.get_default('Company'))},
						{'debit_in_account_currency':1000},
					]
				]},
				{cheque_no:1234},
				{cheque_date: frappe.datetime.add_days(frappe.datetime.nowdate(), -1)},
				{user_remark: 'Test'},
			]);
		},
		() => cur_frm.save(),
		() => {
			// get_item_details
			assert.ok(cur_frm.doc.total_debit==1000, "total debit correct");
			assert.ok(cur_frm.doc.total_credit==1000, "total credit correct");
		},
		() => frappe.tests.click_button('Submit'),
		() => frappe.tests.click_button('Yes'),
		() => frappe.timeout(0.3),
		() => done()
	]);
});
