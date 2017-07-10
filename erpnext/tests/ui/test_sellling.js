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
			console.log(cur_frm.doc.items[0].get_item_details);
		},
		() => done()
	]);
});

QUnit.test("test lead", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Lead', [
				{lead_name: 'Test Customer 1'},
				{status: 'Lead'}
			]);
		},
		() => {
			assert.ok(cur_frm.doc.lead_name=='Test Customer 1');
			assert.ok(cur_frm.doc.status=='Lead');
		},
		() => done()
	]);
});

QUnit.test("test opportunity", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Opportunity', [
				{enquiry_from: 'Lead'},
				{status: 'Open'},
				{enquiry_type: 'Sales'},
				{transaction_date: '2017-07-06'},
				{lead: 'LEAD-00002'}
			]);
			
		},
		() => {
			assert.ok(cur_frm.doc.enquiry_from=='Lead');
			assert.ok(cur_frm.doc.enquiry_type=='Sales')
		},
		() => done()
	]);
});

// Test for creating query report

QUnit.test("test building report", function(assert) {
	assert.expect(2);
	let done = assert.async();
	frappe.run_serially([
		() => {
			return frappe.tests.make('Report', [
				{report_name: 'Selling Report'},
				{report_type: 'Query Report'},
				{ref_doctype: 'Sales Person'},
				{module: 'Setup'}
			]);			
		},
		() => {
			
			assert.ok(cur_frm.doc.report_name=='Selling Report');
			assert.ok(cur_frm.doc.report_type=='Query Report');
		},
		() => done()
	]);
});

//Test for generating report with the help of writing query

QUnit.test("test query report", function(assert) {
	assert.expect(1);
	let done = assert.async();
	frappe.run_serially([
			() => frappe.set_route('Form','Report', 'Selling Report'),

			//Query
			() => cur_frm.set_value('query','Select * from `tabSales Person`'),
			() => cur_frm.save(),   
			
			() => { $("form-inner-toolbar .btn-xs").click(frappe.set_route('query-report','Selling Report')); },	
			() => frappe.timeout(5),
			
			() => assert.deepEqual(["query-report", "Selling Report"], frappe.get_route()),
			() => done()
	]);
});