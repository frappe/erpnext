# Update Stock Option In Sales Invoice

#Delivery from Sales Invoice

If you have items delivery and invoicing happening at the same time, you can create delivery from with Sales Invoice itself. Sales Invoice has field called **Update Stock**, just before Item table. If this field is checked, on submission of Sales Invoice, stock of Item will be deducted from selected Warehouse.

<img alt="Update Stock" class="screenshot" src="{{docs_base_url}}/assets/img/articles/update-stock.png">

On checking Update Stock, Sales Invoice Item will show relevant fields like Warehouse, Serial No., Batch No., Item valuation etc.

On submission of Sales Invoice, with general ledger posting, stock ledger posting will happen as well.
