<h1>Repack Entry</h1>

<h1>Repack Entry</h1>

If you buy items in bulk to be repacked into smaller packs, you can create a **Stock Entry** of type "Repack". For example, item bought in tons can be repacked into Kgs. 

Notes:
1. Separate purchase and repacked Items must be made.
2. Repack entry can be made with or without BOM (Bill of Material).

Let's check below scenario to understand this better.

Assume you buy crude oil in barrel, and get diesel and gasoline as its output. To create production entry, go to:

#### 1. New Stock Entry

`Stock > Documents > Stock Entry > New Stock Entry`

#### 2. Enter Items

Select Purpose as 'Repack Entry'.

For raw-material/input item, only Source Warehouse will be provided.

For repacked/production item, only Target Warehouse will be entered. You will have to provide valuation for the repacked/production item.

![New STE]({{docs_base_url}}/assets/img/articles/Selection_071.png)

#### 3. Submit Stock Entry

On submitting Stock Entry, stock of input item will be reduced from Source Warehouse, and stock of repacked/production item will be added in the Target Warehouse.

![New STE]({{docs_base_url}}/assets/img/articles/Selection_072.png)

<!-- markdown --> 