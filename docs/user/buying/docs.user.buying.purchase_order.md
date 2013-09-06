---
{
	"_label": "Purchase Order"
}
---
A Purchase Order is analogous to a Sales Order. It is usually a binding contract with your Supplier that you promise to buy a set of Items under the given conditions.


A Purchase Order can  be automatically created from a Material Request or Supplier Quotation.


![Purchase Order](img/purchase-order-f.jpg)


In ERPNext, you can also make a Purchase Order directly by going to:

> Buying > Purchase Order > New Purchase Order
￼


![Purchase Order](img/purchase-order.png)




Entering a Purchase Order is very similar to a Purchase Request, additionally you will have to set:

- Supplier. 
- A “Required By” date on each Item: If you are expecting part delivery, your Supplier will know how much quantity to deliver at which date. This will help you from preventing over-supply. It will also help you to track how well your Supplier is doing on timeliness.

### Taxes

If your Supplier is going to charge you additional taxes or charge like a shipping or insurance charge, you can add it here. It will help you to accurately track your costs. Also, if some of these charges add to the value of the product you will have to mention them in the Taxes table. You can also use templates for your taxes. For more information on setting up your taxes see the Purchase Taxes and Charges Master.


### Value Added Taxes (VAT)

Many a times, the tax paid by you to a Supplier, for an Item, is the same tax which you collect from your Customer. In many regions, what you pay to your government is only the difference between what you collect from your Customer and what you pay to your Supplier. This is called Value Added Tax (VAT). 

For example you buy Items worth X and sell them for 1.3X. So your Customer pays 1.3 times the tax you pay your Supplier. Since you have already paid tax to your Supplier for X, what you owe your government is only the tax on 0.3X.

This is very easy to track in ERPNext since each tax head is also an Account. Ideally you must create two Accounts for each type of VAT you pay and collect, “Purchase VAT-X” (asset) and “Sales VAT-X” (liability), or something to that effect. Please contact your accountant if you need more help or post a query on our forums!