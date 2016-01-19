<h1>Serial No. Naming</h1>

<h1>Serial No. Naming</h1>

Serial Nos. are unique value assigned on each unit of an item. Serial no. helps in locating and tracking item's warranty and expiry details.

To make item Serialized, in the Item master, on selecting **Has Serial No** field should be updated as "Yes".

There are two ways Serial no. can be generated in ERPNext.

###1. Serializing Purchase Items

If purchased items are received with Serial Nos. applied by OEM (original equipment manufacturer), you should follow this approach. While creating Purchase Receipt, you shall scan or manually enter Serial nos. for an item. On submitting Purchase Receipt, Serial Nos. will be created in the backend as per Serial No. entered for an item.

If received items already has its Serial No. barcoded, you can simply scan that barcode for entering Serial No. in the Purchase Receipt. Click [here](https://frappe.io/blog/management/using-barcodes-to-ease-data-entry) to learn more about it.

On submission of Purchase Receipt or Stock entry for the serialized item, Serial Nos. will be auto-generated.

![Serial Nos]({{docs_base_url}}/assets/img/articles/Selection_061.png)

Generated Serial numbers will be updated for each item.

![Serial Nos]({{docs_base_url}}/assets/img/articles/Selection_062.png)

###2. Serializing Manufacturing Item

To Serialize Manufacturing Item, you can define Series for Serial No. Generation in the Item master itself. Following that series, system will create Serial Nos. for Item when its Production entry is made.

####2.1 Serial No. Series

When Item is set as serialized, it will allow you to mentioned Series for it.

![Item Serial No. Series]({{docs_base_url}}/assets/img/articles/Selection_049.png)

####2.2 Production Entry for Serialized Item

On submission of production entry for manufacturing item, system will automatically generate Serial Nos. following Series as specified in the Item master.

![Serial No]({{docs_base_url}}/assets/img/articles/Selection_054.png)

<!-- markdown -->