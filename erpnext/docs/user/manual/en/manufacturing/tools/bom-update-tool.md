# BOM Update Tool

From BOM Update Tool, you can replace a sub-assembly BOM and update costs of all BOMs.

### Replace BOM
Using this utility, you can replace an existing BOM of sub-assembly item, with a new one. The system will update the new BOM in all the parent BOMs where it was used.

To use the BOM Update Tool, go to:

> Manufacturing > Tools > BOM Update Tool

Let's consider a scenario to understand this better.

Suppose a company manufactures computers, Bill of Material of of the computer will look like this:

1. Monitor
1. Key Board
1. Mouse
1. CPU

Out of all the items above, CPU is asembled separately. Hence separate BOM will be created for the CPU. Following are the items from the BOM of CPU.

1. 250 GB Hard Disk
1. Mother Board
1. Processor
1. SMTP
1. DVD player

If we have more items to be added , or existing items to be edited in the BOM of CPU, then we should create new BOM for it.

1. _350 GB Hard Disk_
1. Mother Board
1. Processor
1. SMTP
1. DVD player

To update new BOM in all the parent BOMs, where CPU is selected as raw-material, you can use Replace utility.

<img class="screenshot" alt="BOM Update Tool" src="{{docs_base_url}}/assets/img/manufacturing/bom-update-tool.png">

In this tool, you should select Current BOM, and New BOM. On clicking Replace button, current BOM of CPU will be replaced with New BOM in the BOM of finished Item (Computer).

**Will BOM Replace Tool work for replacing finsihed item in BOM?**

No. You should Cancel and Amend current BOM, or create a new BOM for finished item.

### Update BOM Cost
Using the button **Update latest price in all BOMs**, you can update cost of all Bill of Materials, based on latest purchase price / price list rate / valuation rate of raw materials.

On clicking of this buttom, system will create a background process to update all the BOM's cost. It is processed via background jobs because this process can take a few minutes (depending on the number of BOMs) to update all the BOMs.

This functionality can also be executed automatically on daily basis. For that, you need to enable "Update BOM Cost Automatically" from Manufacturing Settings.

{next}
