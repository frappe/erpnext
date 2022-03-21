
context('Customer', () => {
	before(() => {
		cy.login();
	});
	
	it('Insert a Customer and check attributes', () => {
		cy.visit(`app/customer/`);
		cy.get('.primary-action').click();
		cy.get('.custom-actions > .btn').click();
		cy.get_field('customer_group', 'Link').type("All Customer Groups");
		cy.get_field('customer_name', 'Link').type("Lara Schindler");
		cy.get_field('territory', 'Link').type("All Territories");
		cy.get('.modal-footer > .standard-actions > .btn-primary').contains("Save").trigger('click', {force: true});
		cy.get_field('customer_group', 'Link').should('have.value', 'All Customer Groups');
		cy.get_field('customer_name', 'Link').should('have.value', 'Lara Schindler');
		cy.get_field('territory', 'Link').should('have.value', 'All Territories');
		cy.get('#page-Customer > .page-head > .container > .row > .col > .standard-actions > .primary-action').click();
		cy.remove_doc('Customer', 'Lara Schindler');		
	});
});
