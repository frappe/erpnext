### How are Items Valued?

One of the major features of any inventory system is that you can find out the
value of any item based on its historic or average price. You can also find
the value of all your items for your balance sheet.

Valuation is important because:

  * The buying price may fluctuate.
  * The value may change because of some process (value add).
  * The value may change because of decay, loss etc.

You may encounter these terms, so lets clarify:

  * Rate: Rate at which the transaction takes place.
  * Valuation Rate: Rate at which the items value is set for your valuation.

There are two major ways in which ERPNext values your items.

  * **FIFO (First In First Out):** In this system, ERPNext assumes that you will consume / sell those Items first which you bought first. For example, if you buy an Item at price X and then after a few days at price Y, whenever you sell your Item, ERPNext will reduce the quantity of the Item priced at X first and then Y.

<img alt="FIFO" class="screenshot" src="{{docs_base_url}}/assets/img/stock/fifo.png">

  * **Moving Average:** In this method, ERPNext assumes that the value of the item at any point is the average price of the units of that Item in stock. For example, if the value of an Item is X in a Warehouse with quantity Y and another quantity Y1 is added to the Warehouse at cost X1, the new value X2 would be:

> New Value X2 = (X * Y + X1 * Y1) / (Y + Y1)
