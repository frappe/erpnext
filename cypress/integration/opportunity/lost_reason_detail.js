context('Form', () => {
	before(() => {
		cy.login('Administrator', 'qwe');
		cy.visit('/desk');
	});

	it('create a new opportunity', () => {
		cy.visit('/desk#Form/Opportunity/New Opportunity 1');
		cy.get('.page-title').should('contain', 'Not Saved');
		cy.fill_field('enquiry_from', 'Customer', 'Select');
		cy.fill_field('customer', 'Test Customer', 'Link').blur();
		cy.get('.primary-action').click();
		cy.get('.page-title').should('contain', 'Open');
		cy.get('.form-inner-toolbar button:contains("Lost")').click({ force: true });
		cy.get('.modal input[data-fieldname="lost_reason"]').as('input');
		cy.get('@input').focus().type('Higher', { delay: 200 });
		cy.get('.modal .awesomplete ul')
			.should('be.visible')
			.get('li:contains("Higher Price")')
			.click({ force: true });
		cy.get('@input').focus().type('No Followup', { delay: 200 });
		cy.get('.modal .awesomplete ul')
			.should('be.visible')
			.get('li:contains("No Followup")')
			.click();

		cy.fill_field('detailed_reason', 'Test Detailed Reason', 'Text');
		cy.get('.modal button:contains("Declare Lost")').click({ force: true });
		cy.get('.page-title').should('contain', 'Lost');
	});
});

