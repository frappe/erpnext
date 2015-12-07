<h1>Managing Purchase UoM and Stock UoM</h1>

When purchasing an item, you can set purchase UoM (Unit of Measurement) which could be different from item's stock UoM.

### Scenario:

Item ABC is stocked in Nos, but purchased in Cartons. Hence in the Purchase Order, you will need to update UoM as Carton.

### 1. Editing Purchase UoM


#### Step 1.1: Edit UoM in the Purchase Order

In the Purchase Order, you will find two UoM fied.

- UoM
- Stock UoM

In both the fields, default UoM of an item will be updated. You should edit UoM field, and select Purchase UoM (Carton in this case).

![Item Purchase UoM]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 4.10.35 pm.png)

#### Step 1.2: Update UoM Conversion Factor

In one Carton, if you get 20 Nos. of item ABC, then UoM Conversion Factor would be 20. 

![Item Conversion Factor]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 4.11.58 pm.png)

Based on the Qty and Conversion Factor, qty will be calculated in the Stock UoM of an item. If you purchase just one carton, then Qty in the stock UoM will be set as 20.

![Purchase Qty in Default UoM]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 4.14.46 pm.png)

### 2. Stock Ledger Posting

Irrespective of the Purchase UoM selected, stock ledger posting will be done in the Default UoM of an item only. Hence you should ensure that conversion factor is entered correctly while purchasing item in different UoM.

With this, we can conclude that, updating Purchase UoM is mainly for the reference of the supplier. In the print format, you will see item qty in the Purchase UoM.

![Print Format in Purchase UoM]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 4.15.27 pm.png)

### 3. Setting Conversion Factor in the Item master

In the Item master, under Purchase section, you can list all the possible purchase UoM of an item, with its UoM Conversion Factor.

![Purchase UoM master]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-19 at 4.13.16 pm.png)

<!-- markdown -->