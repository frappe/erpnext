##General Overview

We have three branches where all the work happens: 

* **master** - This is the stable branch based on which we do releases. This branch is for production. 
* **develop** - This is an unstable branch for development purposes, it has bleeding edge features and fixes, but it's not recommended for production. Bug fixes and new features go here. 
* **hotfix** - This is a branch dedicated to hotfixes on the master branch. Urgent bug fixes go here. 


Once we deem the develop branch to be stable, we merge it into the master and do a major release. The hotfix branch is solely for making urgent bug fixes on the current master branch, which we then merge into master.

We almost never push directly to master.


***


##Workflow

Contributing to ERPNext is not very different from the usual Pull Request workflow on GitHub.

###Prerequisites : 

* You need to know [Git and Github basics](https://try.github.io/levels/1/challenges/1)
* You need to have a Fork of the [ERPNext repo](https://github.com/frappe/erpnext) in your personal Github account 
* You need to add a [remote](#glossary) for your Forked repository. `git remote add origin [your-erpnext-repo-url]`


###The Process: 

1. Make sure you're in the right branch. **develop** for adding features /  fixing issues and **hotfix** for urgent bug fixes
2. Make your changes
3. Create and checkout a new branch for the changes you've made. `git checkout -b [branch-name]`
4. Add and commit your changes `git commit -am "[commit-message]"
5. If you have been working on sometime for a long time, you should [rebase](#glossary) your branch with our develop branch. `git pull upstream develop --rebase` where `upstream` is the remote name of our repo
6. Now, push your changes to your fork. `git push origin [branch-name]`   
If you rebased your commits, you will have to [force push](http://vignette2.wikia.nocookie.net/starwars/images/e/ea/Yodapush.png/revision/latest?cb=20130205190454) `git push origin [branch-name] --force`
7. You should now be able to see your pushed branch on Github, now create a pull request against the branch that you want to merge to.
8. Wait for us to review it

###Common Problems: 

* During rebase you might face _merge conflicts_. A merge conflict occurs when you have made changes to the same file that someone else has, in the commits you're pulling. You need to resolve these conflicts by picking which code you want to keep, yours or theirs. You can use `git mergetool` for help.
* Sometimes you don't have a local branch to which you want to make changes to. In that case you first run `git fetch` followed by `git checkout --track -b upstream/[branch-name]`
 

###Good practices: 

* You should rebase your branch with the branch you plan to make a Pull Request to as often as you can. 
* Your commit messages should be precise and explain exactly what the commit does. Same goes for the Pull Request title.
* When making a PR make sure that all your code is committed properly by checking the diffs.
* If you're working on different things at the same time, make sure you make separate branches for each.
* Don't create new DocTypes unless absolutely necessary. If you find that there is a another DocType with a similar functionality, then please try and extend that functionality.
* DRY. Don't Repeat Yourself. Before writing up a similar function /feature make sure it doesn't exist in the codebase already. 
* Tabs, not spaces.


###Glossary

* remote - A remote is a connection to a Github repo. You should have two remotes, one that points to your repo and one to ours. 
* rebase - When you rebase a branch, you pull commits from your remote branch and move your commits on top of it. This allows you to update your branch with the latest changes without losing  your changes.
