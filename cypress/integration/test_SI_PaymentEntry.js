
context('Sales Invoice Payment', () => {
	before(() => {
		cy.login();
	});

	it('Create Sales Invoice', () => {
		cy.visit('app/sales-invoice');
        cy.insert_doc(
            "Sales Invoice",
            {
                naming_series: "SINV-.YY.-",
                posting_date: "2022-05-18",
                customer: "Nidhi - 1",
                due_date: "2022-05-18",
                items: [{"item_code": "Solid Wood 4-Seater Dinning Table Set1", "qty": 1, "rate": 8000, "amount": 8000}]
            },
            true
        ).then((d)=>{ 
            console.log(d);
            cy.visit('app/sales-invoice/'+ d.name);
            cy.findByRole('button', {name: 'Submit'}).click();
            cy.findByRole('button', {name: 'Yes'}).click();
            cy.get('.page-title').should('contain', 'Unpaid');
        });
	});

    it('Create Sales Invoice Payment', () => {
        cy.findByRole('button', {name: 'Create'}).click();
        cy.get('[data-label="Payment"]').click();
		cy.get_field('payment_type', 'Select').should('have.value', 'Receive');
        cy.get_field('paid_amount', 'Currency').should('have.value', '8,000.00');
       // cy.get_field('reference_name', 'Dynamic Link').should('have.value', );
		cy.get_field('reference_no', 'Data').type('ABC-123');
        cy.get_field('reference_date', 'Date').click();  //Opens calendar
		cy.get('.datepicker.active > .datepicker--buttons > .datepicker--button').click();
        cy.findByRole('button', {name: 'Save'}).click();
        cy.get('.page-title').should('contain', 'Draft');
		cy.findByRole('button', {name: 'Submit'}).click();
        cy.findByRole('button', {name: 'Yes'}).click();
    });

	it('Check Payment Entry Values', () => {
		cy.get('.page-title').should('contain', 'Submitted');

	});

	// after(() => {
	// });
});
