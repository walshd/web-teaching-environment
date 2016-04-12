Module Access Settings
----------------------

By default any module that is available to learners (see :doc:`../status`) can be taken
by any learner. However, sometimes you may want to restrict access to a module. To do so,
move your mouse over the module's :icon:`fi-list` icon and then select the
:dropdown_link:`Edit Access Settings<fi-key>` menu item.

Access to modules in the WTE can be restricted based on two criteria: password and e-mail
domain.

Password access
^^^^^^^^^^^^^^^

To limit access to the module to those learners who know the right password, first select
the "Password required" checkbox. Then type the password you wish to use into the "Password"
text box. Click on the :primary_btn:`Update` button to make the access restriction active.

After you have set a password, when a learner goes to the module page and wishes to take
the module, they need to enter the same password and will only be granted access if the
passwords match. Learners who are already taking the module are not affected by this and
will continue to have access. Also you can always add learners via the :doc:`user management <users>`
interface.

E-Mail domain access
^^^^^^^^^^^^^^^^^^^^

You can also restrict access to those learners who have registered with e-mail addresses
that belong to one or more domains that you specify (the domain is the part after the @ sign).

To limit access by e-mail domain select the "E-mail domain limited" checkbox and then enter
the e-mail domain(s) that are allowed access into the "Allowed e-mail domains" text box.
You can specify multiple e-mail domains, separated by commas. If you specify multiple
domains, then a learner is granted acccess to the module if their e-mail domain matches
any one of the listed domains.

Multiple access criteria
^^^^^^^^^^^^^^^^^^^^^^^^

If you select more than one of the access criteria, then for the learner to be granted
access to the module, they must fulfill **all** criteria.
