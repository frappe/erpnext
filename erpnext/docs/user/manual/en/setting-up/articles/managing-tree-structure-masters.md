<h1>Managing Tree Structure Masters</h1>

<h1>Managing Tree Structure Masters</h1>

Some of the masters in ERPNext are maintained in tree structure. Tree structured masters allow you to set Parent masters, and Child masters under those Parents. Setting up this structure allows you creating intelligent report, and track growth at each level in the hierarchy. 

Following is the partial list of masters which are maintained in the tree structure.

* Chart of Accounts

* Chart of Cost Centers

* Customer Group

* Territory

* Sales Person

* Item Group

Following are the steps to manage and create record in the tree structured master. Let's consider Territory master to understand managing tree masters.

####Step 1 : Go to Master

`Selling > Setup > Territory`

Also you can type master name in Awesome Bar to go to the related master.

Tree master allows you to set Parent Territories, and Child Territories Groups under those Parents.

####Step 2 : New Parent Territory

![Territory Group]({{docs_base_url}}/assets/img/articles/Sselection_013.png)

When click on Parent Territory, you will see option to add child territory under it. All default Territory groups will be listed under parent group called "All Territories". You can add further parent or child Territory Groups under it.

####Step 3: Name The Territory Group

When click on Add Child, a dialog box will provide two fields.

**Territory Group Name**

Territory will be saved with Territory Name provided here.

**Group Node**

If Group Node selected as Yes, then this Territory will be created as Parent, which means you can further create sub-territories under it. If select No, then it will become child Territory which you will be able to select in another masters.

<div class="well">Only child Territory Groups are selectable in another masters and transactions.</div>
![Child Territory]({{docs_base_url}}/assets/img/articles/Selection_0124080f1.png)

Following is how Child Territories will be listed under a Parent Territory.

![Territory Tree]({{docs_base_url}}/assets/img/articles/Selection_014.png)

Following this steps, you can manage other tree masters in ERPNext.

<!-- markdown -->