# Module Visibility

#Module Visibility

If you have permission on specific module, but it is still not visible, following are the possibilities of issues you should look at. Let's consider a scenario that user is permission of Website module, but not able to access it.

As step zero, ensure that you have "Website Manager" role assigned. It is a standard Role which grants permission on Website module. If permissions has been customized in your account, check Role Permission Manager to know which Role has permission on Website, and then check if same Role is assigned to User.

If module is hidden in-spite of assignment of required Role, then you should check if Website is not disabled from All Application.

<img alt="All Applications" class="screenshot" src="{{docs_base_url}}/assets/img/articles/module-visibility-1.gif">

If Website is checked in All Application, but still not visible for the User, check if is hidden by System Manager. In the Setup module, feature called Show/Hide Modules allows System Manager to hide specific module from all the Users.

`Setup > Settings > Show / Hide Modules`

Ensure Website module is checked. If you just enabled/activated it, update Show/Hide Module page, and then Reload tab of your ERPNext account. After reload, changes made in the Setup module will be applied and will be visible in the system.

On the same lines, you can check for the visibility issue of other modules as well.

<!-- markdown -->