QUnit.module('accounts');

QUnit.test("test account with number", function(assert) {
	assert.expect(7);
	let done = assert.async();
	frappe.run_serially([
		() => frappe.set_route('Tree', 'Account'),
		() => frappe.click_link('Income'),
		() => frappe.click_button('Add Child'),
		() => frappe.timeout(.5),
		() => {
			cur_dialog.fields_dict.account_name.$input.val("Test Income");
			cur_dialog.fields_dict.account_number.$input.val("4010");
		},
		() => frappe.click_button('Create New'),
		() => frappe.timeout(1),
		() => {
			assert.ok($('a:contains("4010 - Test Income"):visible').length!=0, "Account created with number");
		},
		() => frappe.click_link('4010 - Test Income'),
		() => frappe.click_button('Edit'),
		() => frappe.timeout(.5),
		() => frappe.click_button('Update Account Number'),
		() => frappe.timeout(.5),
		() => {
			cur_dialog.fields_dict.account_number.$input.val("4020");
		},
		() => frappe.timeout(1),
		() => cur_dialog.primary_action(),
		() => frappe.timeout(1),
		() => cur_frm.refresh_fields(),
		() => frappe.timeout(.5),
		() => {
			var abbr = frappe.get_abbr(frappe.defaults.get_default("Company"));
			var new_account = "4020 - Test Income - " + abbr;
			assert.ok(cur_frm.doc.name==new_account, "Account renamed");
			assert.ok(cur_frm.doc.account_name=="Test Income", "account name remained same");
			assert.ok(cur_frm.doc.account_number=="4020", "Account number updated to 4020");
		},
		() => frappe.timeout(1),
		() => frappe.click_button('Menu'),
		() => frappe.click_link('Rename'),
		() => frappe.timeout(.5),
		() => {
			cur_dialog.fields_dict.new_name.$input.val("4030 - Test Income");
		},
		() => frappe.timeout(.5),
		() => frappe.click_button("Rename"),
		() => frappe.timeout(2),
		() => {
			assert.ok(cur_frm.doc.account_name=="Test Income", "account name remained same");
			assert.ok(cur_frm.doc.account_number=="4030", "Account number updated to 4030");
		},
		() => frappe.timeout(.5),
		() => frappe.click_button('Chart of Accounts'),
		() => frappe.timeout(.5),
		() => frappe.click_button('Menu'),
		() => frappe.click_link('Refresh'),
		() => frappe.click_button('Expand All'),
		() => frappe.click_link('4030 - Test Income'),
		() => frappe.click_button('Delete'),
		() => frappe.click_button('Yes'),
		() => frappe.timeout(.5),
		() => {
			assert.ok($('a:contains("4030 - Test Account"):visible').length==0, "Account deleted");
		},
		() => done()
	]);
});
