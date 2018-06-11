# Blanket Order

Blanket Order is a order where a party can place order which will be delivered over a period of time. This gives bussiness
an advantage as the price of items can be better negotiated for larger quantities and determined for future orders.

In ERPNext, you can create the Blanket Order as the selling or purchasing type. For selling type blanket orders, you have to select the Customer and for purchasing type blanket orders, you have to select the Supplier.

Once you submit a Blanket Order, you can create the Sales Order / Purchase Order within the Blanket Order itself via clicking on the Create Order button.

<img class="screenshot" alt="Blanket Order" src="{{docs_base_url}}/assets/img/stock/blanket-order.gif">

> Note: If there is a valid Blanket Order for a particular Customer / Supplier, and you are creating the Sales / Purchase order then the rate of the Items will be fetched from the Blanket Order.


For every order created against the Blanket Order, a linking will be done and total ordered quantity will be updated in the Blanket Order.

You can also manually select the Blanket Order in the Sales / Purchase order.
