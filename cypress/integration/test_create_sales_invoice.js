
context('Sales Invoice Creation', () => {
	before(() => {
		cy.login();
	});

	it('Create Sales Order', () => {
        cy.visit('app/sales-order');
		cy.click_listview_primary_button('Add Sales Order');
        cy.insert_doc(
            "Sales Order",
            {
                naming_series: "SAL-ORD-.YYYY.-",
                transaction_date: "2022-05-17",
                customer: "Nidhi - 1",
                order_type: "Sales",
                items: [{"item_code": "Solid Wood 4-Seater Dinning Table Set1", "delivery_date": "2022-05-17", "qty": 1}]
            },
            true
        ).then((d)=>{ 
            console.log(d);
            cy.visit('app/sales-order/'+ d.name);
            cy.findByRole('button', {name: 'Submit'}).click();
            cy.findByRole('button', {name: 'Yes'}).click();
            cy.get('.page-title').should('contain', 'To Deliver and Bill');
        });
	});

    it('Create Sales Invoice', () => {
        cy.visit('app/sales-order/');
        cy.click_listview_row_item(0);
        cy.get('.form-documents > :nth-child(1) > :nth-child(1) > :nth-child(2) > .btn > .icon').click();  //Click on + icon on SO to open SI
        cy.findByRole('button', {name: 'Save'}).click();
        cy.get('.page-title').should('contain', 'Draft');
	    cy.wait(500);
		cy.findByRole('button', {name: 'Submit'}).click();
        cy.findByRole('button', {name: 'Yes'}).click();
		cy.get('.page-title').should('contain', 'Unpaid');
    });

});
