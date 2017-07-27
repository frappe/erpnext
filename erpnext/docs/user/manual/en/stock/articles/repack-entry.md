#Repack Entry

Repack Entry is created for item bought in bulk, which is being packed into smaller packages. For example, item bought in tons can be repacked into Kgs. 

Notes:
1. Purchase Item and repack will be have different Item Codes.
2. Repack entry can be made with or without BOM (Bill of Material).

In a Repack Entry, there can be one or more than one repack items. Let's check below scenario to understand this better.

Assume we are buying boxes of spray paint of specific colour (Green, Blue etc). And later re-bundling to create packs having multiple colours of spray paint (Blue-Green, Green-Yellow etc.) in them.

#### 1. New Stock Entry

`Stock > Documents > Stock Entry > New Stock Entry`

#### 2. Enter Items

Select Purpose as 'Repack Entry'.

For raw-material/input item, only Source Warehouse will be provided.

For repacked/output items, only Target Warehouse will be provided. You will have to provide valuation for the repack items.

<img alt="Repack Entry" class="screenshot" src="{{docs_base_url}}/assets/img/articles/repack-1.png">

Update Qty for all the items selected.

#### 3. Submit Stock Entry

On submitting Stock Entry, stock of input item will be reduced from Source Warehouse, and stock of repack/output item will be added in the Target Warehouse.

<img alt="Repack Stock Entry" class="screenshot" src="{{docs_base_url}}/assets/img/articles/repack-2.png">

<!-- markdown --> 