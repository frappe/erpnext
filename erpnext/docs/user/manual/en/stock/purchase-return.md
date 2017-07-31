# Purchase Return

ERPNext has an option for products that are need to be returned to the
supplier. This may be on account of a number of reasons like defects in goods,
quality not matching, the buyer not needing the stock, etc.

You can create a Purchase Return by simply making a Purchase Receipt with negative quantity.

First open the original Purchase Receipt, against which supplier delivered the items.

<img class="screenshot" alt="Original Purchase Receipt" src="/docs/assets/img/stock/purchase-return-original-purchase-receipt.png">

Then click on "Make Purchase Return", it will open a new Purchase Receipt with "Is Return" checked, items and taxes with negative amount.

<img class="screenshot" alt="Return Against Purchase Receipt" src="/docs/assets/img/stock/purchase-return-against-purchase-receipt.png">

On submission of Return Purchase Return, system will decrease item qty from the mentioned warehouse. To maintain correct stock valuation, stock balance will also go up according to the original purchase rate of the returned items.

<img class="screenshot" alt="Return Stock Ledger" src="/docs/assets/img/stock/purchase-return-stock-ledger.png">

If Perpetual Inventory enabled, system will also post accounting entry against warehouse account to sync warehouse account balance with stock balance as per Stock Ledger.

<img class="screenshot" alt="Return Stock Ledger" src="/docs/assets/img/stock/purchase-return-general-ledger.png">