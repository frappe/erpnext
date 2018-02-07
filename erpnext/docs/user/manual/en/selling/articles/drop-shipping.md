#Drop Ship

**Drop shipping** is a supply chain management technique in which the retailer does not keep goods in stock. Instead they transfer customer orders and shipment details to either the manufacturer, another retailer, or a wholesaler, who then ships the goods directly to the customer

In ERPNext, you can create a Drop Shipping by creating Purchase Order against Sales Order.

> Selling > Documents > Sales Order > Purchase Order

#### Setup on Item Master

Set **_Delivered by Supplier (Drop Ship)_** and **_Default Supplier_** in Item Master.

<img class="screenshot" alt="Setup Item Master" src="{{docs_base_url}}/assets/img/selling/setup-drop-ship-on-item-master.png">

#### Setup on Sales Order
If Drop Shipping has set on Item master, it will automatically set **Supplier delivers to Customer** and **Supplier** on Sales Order Item.

You can setup Drop Shipping, on Sales Order Item. Under **Drop Ship** section, set **Supplier delivers to Customer** and select **Supplier** agaist which Purchase Order will get created.

<img class="screenshot" alt="Setup Drop Shipping on Sales Order Item" src="{{docs_base_url}}/assets/img/selling/setup-drop-ship-on-sales-order-item.png">

#### Create Purchase Order
After submitting a Sales Order, create Puchase Order.

<img class="screenshot" alt="Setup Drop Shipping on Sales Order Item" src="{{docs_base_url}}/assets/img/selling/drop-ship-sales-order.png">

From Sales Order, all items, having **Supplier delivers to Customer**  checked or **Supplier**(matching with supplier selected on For Supplier popup) mentioned, will get mapped onto Purchase Order. 

It will automatically set Customer, Customer Address and Contact Person.

After submitting Purchase Order, to update delivery status, use **Mark as Delivered** button on Purchase Order. It will update delivery percetage and delivered quantity on Sales Order.

<img class="screenshot" alt="Purchase Order for Drop Shipping" src="{{docs_base_url}}/assets/img/selling/drop-ship-purchase-order.png">

<span style="color:#18B52D">**_Close_**</span>, is a new feature introduced on **Purchase Order** and **Sales Order**, to close or to mark fulfillment.

<img class="screenshot" alt="Close Sales Order" src="{{docs_base_url}}/assets/img/selling/close-sales-order.png">

###Drop Shipping Print Format
You can notify, Suppliers by sending a email after submitting Purchase Order by attaching Drop Shipping print format.

<img class="screenshot" alt="Drop Dhip Print Format" src="{{docs_base_url}}/assets/img/selling/drop-ship-print-format.png">

###Video Help on Drop Ship

<iframe width="660" height="371" src="https://www.youtube.com/embed/hUc0hu_XLdo" frameborder="0" allowfullscreen></iframe>