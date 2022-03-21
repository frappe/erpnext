
context('Supplier', () => {
	before(() => {
		cy.login();
	});
  
	it('Insert a Supplier', () => {
		cy.visit(`app/supplier/`);
		cy.get('.primary-action').click();
		cy.get('.custom-actions > .btn').click();
		cy.get_field('supplier_group', 'Link').type("All Supplier Groups");
		cy.get_field('supplier_name', 'Link').type("Medlink International Suppliers");
		cy.get('#page-Supplier > .page-head > .container > .row > .col > .standard-actions > .primary-action').click();
		cy.get_field('supplier_name', 'Link').should('have.value', 'Medlink International Suppliers');
		cy.get_field('supplier_group', 'Link').should('have.value', 'All Supplier Groups');	
		cy.get('#page-Supplier > .page-head > .container > .row > .col > .standard-actions > .primary-action').click();
		cy.remove_doc('Supplier', 'Medlink International Suppliers');
	});
});
