
context('Create Customer', () => {
	before(() => {
		cy.login();
	});

	it('Create Customer', () => {
		cy.visit(`app/customer`);
		cy.click_listview_primary_button('Add Customer');
		cy.contains('Edit in full page').click();
        cy.get_field('customer_name', 'Data').type('Nidhi');
		cy.get_field('customer_type', 'Select').should('have.value', 'Company');
		cy.get_field('customer_group', 'Link').type('Commercial');
        cy.get_field('territory', 'Link').type('All Territories');
		cy.get('.form-page > :nth-child(5) > .section-head > .ml-2 > .icon > .mb-1').click(); //click to expand 'Currency and Price List' section
		cy.get_field('default_currency', 'Link').type('INR');
		cy.findByRole('button', {name: 'Save'}).click();
	});

	it('Check customer form values', () => {
		cy.get('.page-title').should('contain', 'Nidhi');
		cy.get('.page-title').should('contain', 'Enabled');
		cy.get_field('customer_name', 'Data').should('have.value', 'Nidhi');
	});

	it('Opening SO from Customer', () => {
		cy.get('.form-documents > :nth-child(1) > :nth-child(2) > :nth-child(2) > .btn > .icon').click(); // Click on + to create Sales Order
		cy.get_field('order_type', 'Select').should('have.value', 'Sales');
	});

	after(() => {
		cy.remove_doc('Customer', 'Nidhi');
	});
});
