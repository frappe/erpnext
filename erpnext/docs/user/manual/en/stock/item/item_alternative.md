# Item Alternatives

Item Alternative is the table holding the relation between an Item (parent) and other Items (child).
This feature is used for production order and manufacturing purposes as an Item during the manufacture process can have the alterative in stock.

Relation is defined as One-Way or Two-Way between Item and another Item with specific Unit of Measurement.

1. One-Way: An Item can have alternative of another Item but not the other way, meaning the other Item is not related to Item.
2. Two-Way: An Item can have alternative of another Item and auto sets another Item relation to Item.


A practical example explaining the concept:

You company produce/manufactures T-shirts. A T-shirt can be red by using paint from 2 suppliers (Paint-1 , Paint-2).
Paints are 2 new Items in the Item-Group T-Shirt Paints.

Setting up alternative should be, in Paint-1 we have Two-Way relation with Paint-2.

This means that during BOM and Production Order, a T-shirt can have both Paint-1, Paint-2 as selection in Manufacture.
So, during manufacture if Paint-1 is ending, user can select safely Paint-2 and continue the manufacturing process.


There are two ways to reach to new Item Price form.

> Stock >> Setup >> Item Alternatives >> New Item Alternatives

Or

> Item >> Add/Edit Item Alternatives >> Click on "+"  >> New Item Alternatives


Naming Series for Item Alternatives: ITEM-ALTERNATIVE-.#####
