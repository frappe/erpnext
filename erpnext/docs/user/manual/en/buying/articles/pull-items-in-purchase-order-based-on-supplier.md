#Pull Items in Purchase Order based on Supplier

**Question:**

Our Material Request has many items, each purchased from different suppliers. How to pull items from all open Material Request which are to be purchased from common Supplier?

**Answer:**

To pull items from Material Request for specific Supplier only, follow below given steps.

####Step 1:  Default Supplier

Update Default Supplier in the Item master.

<img alt="Item Purchase UoM" class="screenshot" src="/docs/assets/img/articles/for-supplier-2.png">

####Step 2:  New Purchase Order

`Buying > Document > Purchase Order > New`

####Step 3:  Select for Supplier

From the options available to pull data in the Purchase Order, click on `For Supplier`.

<img alt="Item Purchase UoM" class="screenshot" src="/docs/assets/img/articles/for-supplier-1.gif">

####Step 4: Get Items

Select Supplier name and click on `Get`.

<img alt="Item Purchase UoM" class="screenshot" src="/docs/assets/img/articles/for-supplier-3.png">

####Step 5: Edit Items

All the items associated with a Material Request and having the default Supplier will be fetched in the Items Table. You can further edit items to enter rate, qty etc. Also items which are not to be ordered can be removed from Item table.