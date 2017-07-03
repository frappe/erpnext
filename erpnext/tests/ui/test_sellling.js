QUnit.module('sales');

QUnit.test("test: lead", function(assert) {
    assert.expect(1);
    let done = assert.async();
    let random = frappe.utils.get_random(10);
    frappe.run_serially([
        () => frappe.tests.setup_doctype('Lead'),
        () => frappe.set_route('List', 'Lead'),
        () => frappe.new_doc('Lead'),
        () => cur_frm.set_value('lead_name', random),
        () => cur_frm.save(),
        () => {
            assert.ok(cur_frm.doc.lead_name.includes(random));
            return done();
        }
    ]);
});

QUnit.test("test: opportunity", function(assert) {
    assert.expect(1);
    let done = assert.async();
    frappe.run_serially([
        () => frappe.tests.setup_doctype('Lead'),
        () => {
            return frappe.tests.make('Opportunity', [{
                    enquiry_from: 'Lead'
                },
                {
                    lead: 'LEAD-00001'
                }
            ]);
        },
        () => {
            assert.ok(cur_frm.doc.lead == 'LEAD-00001');
            return done();
        }
    ]);
});

QUnit.test("test: quotation", function(assert) {
    assert.expect(2);
    let done = assert.async();
    frappe.run_serially([
        () => frappe.tests.setup_doctype('Customer'),
        () => frappe.tests.setup_doctype('Item'),
        () => {
            return frappe.tests.make('Quotation', [{
                    customer: 'Test Customer 1'
                },
                {
                    items: [
                        [{
                                'item_code': 'Test Product 1'
                            },
                            {
                                'qty': 5
                            }
                        ]
                    ]
                }
            ]);
        },
        () => {
            // get_item_details
            assert.ok(cur_frm.doc.items[0].item_name == 'Test Product 1');

            // calculate_taxes_and_totals
            assert.ok(cur_frm.doc.grand_total == 500);
        },
        () => done()
    ]);
});
