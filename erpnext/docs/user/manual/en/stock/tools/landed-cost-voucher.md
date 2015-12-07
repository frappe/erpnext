Landed Cost is the total cost of a product to reach the product at the buyer’s door. Landed costs include the original cost of the item, complete shipping costs, customs duties, taxes, insurance and currency conversion fees etc. All of these components might not be applicable in every shipment, but relevant components must be considered as a part of the landed cost.

> To understand landed cost better, let’s take an example based on our daily lives. You need to purchase a new washing machine for your home. Before making actual purchase, you probably do some investigation to know the best price. In this process, you often found a better deal from a store which is long away from your home. But you should also consider shipping cost while buying from that store. Total cost including transportation might be more than the price you get in your nearby store. In that case you will choose to buy from  your nearest store, as landed cost of the item is cheaper in the nearest store.

Similarly in business, identifying landed cost for a item / product is very crucial, as it helps to decide selling cost of that item and impacts company’s profitability. Hence all applicable landed cost charges should be included in item’s valuation rate.

According to the [Third-Party Logistics Study](http://www.3plstudy.com/), only 45% of the respondents stated that they use Landed Cost extensively. The main reasons of not using Landed Cost are unavailability of necessary data (49%), lack of right tools (48%), do not have sufficient time (31%) and not sure how to apply landed cost (27%).

### Landed Cost via Purchase Receipt

In ERPNext, you can add landed cost related charges in “Taxes and Charges” table while creating Purchase Receipt (PR). You should add those charges for “Total and Valuation” or “Valuation”. Charges which are payable to the same supplier from whom you are buying the items, should be tagged as “Total and Valuation”. Otherwise if applicable charges are payable to a 3rd party, it should be tagged as “Valuation”. On submission of PR, system will calculate landed cost of all items, considering those charges and that landed cost will be considered to calculate item’s valuation rate (based on FIFO / Moving Average method).

But in reality, while making Purchase Receipt we might not know all the charges which are applicable for landed cost. Your transporter can send the invoice after 1 month, but there is no point in waiting for booking Purchase Receipt till then. Companies who imports their products / parts, pays a huge amount as Customs Duty. And generally they get invoices from Customs Department after a period of time. In these cases, “Landed Cost Voucher” becomes handy, as it allows you to add those additional charges on a later date, and to update landed cost of purchased items.

### Landed Cost Voucher

You can update landed cost any time in the future via Landed Cost Voucher.

> Stock > Tools > Landed Cost Voucher

In the document, you can select multiple Purchase Receipts and fetch all items from those Purchase Receipts. Then you should add applicable charges in “Taxes and Charges” table. You can easily delete an item if the added charges is not applicable to that item. The added charges are proportionately distributed among all the items based their amount.

<img class="screenshot" alt="Landed Cost Vouher" src="{{docs_base_url}}/assets/img/stock/landed-cost.png">

### What happend on submission?

1. On submission of Landed Cost Voucher, the applicable landed cost charges are updated in Purchase Receipt Item table.

2. Valuation Rate of items are recalculated based on new landed cost. 

3. If you are using “Perpetual Inventory”, the system will post general ledger entries to correct Stock-in-Hand balance. It will debit (increase) corresponding “warehouse account” and credit (decrease) “Expense Included in Valuation” account. If items are already delivered, the Cost-of-Goods-Sold (CoGS) value has been booked as per old valuation rate. Hence, general ledger entries are reposted for all future outgoing entries of associated items, to correct CoGS value.

{next}
