#Material consumption

Material Consumption functionality allows you to have multiple consumption `Stock Entry` against a Work Order. To enable this, go to Manufacturing > Manufacturing Settings.

<img class="screenshot" alt="Item Alternative" src="{{docs_base_url}}/assets/img/manufacturing/allow-material-consumption.png">

Once enabled, a `Material Consumption` button will be available in Work Order once started.

<img class="screenshot" alt="Item Alternative" src="{{docs_base_url}}/assets/img/manufacturing/material-consumption-button.png">

When button is clicked, it will do the following:

1.  It will create Stock Entry with purpose `Material Consumption for Manufacture`.

<img class="screenshot" alt="Item Alternative" src="{{docs_base_url}}/assets/img/manufacturing/material-consumption-for-manufacture.png">

2.  If the "Backflush Raw Materials Based On" in the Manufacturing Settings is set to `BOM`, if will propose to consume all required qty for manufacture.
3.  If the "Backflush Raw Materials Based On" in the Manufacturing Settings is set to `Material Transferred for Manufacture`, if will propose to consume all transferred qty for manufacture.
4.  Once submitted, it will update `Consumed Qty` column in the Work Order.

<img class="screenshot" alt="Item Alternative" src="{{docs_base_url}}/assets/img/manufacturing/consumed-qty.png">

5.  In succeeding Material Consumption, it will suggest unconsumed qty.
6.  Once "Finish" button is clicked in Work Order, it will take into account consumed qty.

### Validations

* If "Allow Multiple Material Consumption" is not set in Manufacturing Settings but "Material Consumption for Manufacture" is use in Stock Entry.

<img class="screenshot" alt="Item Alternative" src="{{docs_base_url}}/assets/img/manufacturing/material-consumption-stock-entry.gif">

* Cannot cancel "Material Consumption for Manufacture" for completed Work Order.

<img class="screenshot" alt="Item Alternative" src="{{docs_base_url}}/assets/img/manufacturing/cancel-material-consumption-stock-entry.gif">
