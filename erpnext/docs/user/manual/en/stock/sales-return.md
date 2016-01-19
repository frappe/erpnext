Goods sold being returned is quite a common practice in business. They could
be returned by the customer on quality issues, non-delivery on agreed date, or
any other reason. 

In ERPNext, you can create a Sales Return by simply making a Delivery Note / Sales Invoice with negative quantity.

First open the original Delivery Note / Sales Invoice, against which customer returned the items.

<img class="screenshot" alt="Original Delivery Note" src="{{docs_base_url}}/assets/img/stock/sales-return-original-delivery-note.png">

Then click on "Make Sales Return", it will open a new Delivery Note with "Is Return" checked, items and taxes with negative amount.

<img class="screenshot" alt="Return Against Delivery Note" src="{{docs_base_url}}/assets/img/stock/sales-return-against-delivery-note.png">

You can also create the return entry against original Sales Invoice, to return stock along with credit note, check "Update Stock" option in Return Sales Invoice.

<img class="screenshot" alt="Return Against Sales Invoice" src="{{docs_base_url}}/assets/img/stock/sales-return-against-sales-invoice.png">

On submission of Return Delivery Note / Sales Invoice, system will increase stock balance in the mentioned warehouse. To maintain correct stock valuation, stock balance will go up according to the original purchase rate of the returned items.

<img class="screenshot" alt="Return Stock Ledger" src="{{docs_base_url}}/assets/img/stock/sales-return-stock-ledger.png">

In case of Return Sales Invoice, Customer account will be credited and associated income and tax account will be debited.

If Perpetual Inventory enabled, system will also post accounting entry against warehouse account to sync warehouse account balance with stock balance as per Stock Ledger.

<img class="screenshot" alt="Return Stock Ledger" src="{{docs_base_url}}/assets/img/stock/sales-return-general-ledger.png">