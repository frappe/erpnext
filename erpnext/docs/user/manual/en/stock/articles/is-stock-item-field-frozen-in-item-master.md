<h1>Is Stock Item field Frozen in the Item master</h1>

<h1>Is Stock Item field Frozen in the Item master</h1>

In the item master, you might witness values in the following fields be frozen.

1. Is Stock Item
1. Has Batch No.
1. Has Serial No.

![Item Field Frozen]({{docs_base_url}}/assets/img/articles/Screen Shot 2015-02-16 at 2.52.56 pm.png)

For an item, once stock ledger entry is created, values in these fields will be froze. This is to prevent user from changing value which can lead to mis-match of actual stock, and stock level in the system of an item.

For the serialized item, since its stock level is calculated based on count of available Serial Nos., setting Item as non-serialized mid-way will break the sync, and item's stock level shown in the report will not be accurate, hence Has Serial No. field is froze.

To make these fields editable once again, you should delete all the stock transactions made for this item. For the Serialized and Batch Item, you should also delete Serial No. and Batch No. record for this item.

<!-- markdown -->