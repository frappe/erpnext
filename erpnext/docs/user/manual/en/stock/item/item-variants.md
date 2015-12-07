A Item Variant is a different version of a Item, such as differing sizes or differing colours.
Without Item variants, you would have to treat the small, medium and large versions of a t-shirt as three separate Items; 
Item variants let you treat the small, medium and large versions of a t-shirt as variations of the same Item.

To use Item Variants in ERPNext, create an Item and check 'Has Variants'

* The Item shall then be referred as a 'Template'

<img class="screenshot" alt="Has Variants" src="{{docs_base_url}}/assets/img/stock/item-has-variants.png">

On selecting 'Has Variants' a table shall appear. Specify the variant attributes for the Item in the table.
In case the attribute has Numeric Values, you can specify the range and increment values here. 

<img class="screenshot" alt="Valid Attributes" src="{{docs_base_url}}/assets/img/stock/item-attributes.png">

> Note: You cannot make Transactions against a 'Template'

To create 'Item Variants' against a 'Template' select 'Make Variants'

<img class="screenshot" alt="Make Variants" src="{{docs_base_url}}/assets/img/stock/make-variant.png">

<img class="screenshot" alt="Make Variants" src="{{docs_base_url}}/assets/img/stock/make-variant-1.png">

To learn more about setting Attributes Master check [Item Attributes]({{docs_base_url}}/user/manual/en/stock/setup/item-attribute.html)
