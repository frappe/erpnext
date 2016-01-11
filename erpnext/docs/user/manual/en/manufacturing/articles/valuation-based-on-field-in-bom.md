#Valuation Based On' Field in BOM

**Question:** What do the various options in <i>Valuation Based On </i>Field in Bill Of Materials (BOM) Form mean? 

**Answer:** There are 3 available options in the <i>Valuation Based On</i> field;

<img src="{{docs_base_path}}/assets/img/articles/kb_bom_field.png">

Valuation Rate: Item valuation rate is defined based on it's purchase/manufacture value + other charges. 

For Purchase Item, it is defined based on charges entered in the Purchase Receipt. If you don't have any Purchase Receipt
 made for an item or a Stock Reconciliation, then you won't have 
Valuation Rate for that item.

Price List Rate: Just like you pull item prices in sales and purchase transaction, it can be pulled in BOM via Price List Rate.   

Last Purchase Rate: It will be the last Purchase Rate value of an item. This value is updated in the item master as well, based on rate in the Purchase Order for this item.