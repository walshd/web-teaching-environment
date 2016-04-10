Module
======

The module is the main high-level structuring element in the Web Teaching Environment.
It contains a number of :doc:`parts <../part/index>` that divide the module's content
into multiple sections. In addition to this a module also defines
:doc:`access settings <access_settings>` that specify restrictions on which learners
can take the module and you can then also :doc:`manage those learners (or tutors) <users>`
that are taking the module.

The following actions are available on modules via the :icon:`fi-list` menu icon, both on
the module overview page and also for each module on the list of your modules:

+------------------------+----------------------+-------------------------+
| Icon                   | Label                | Action                  |
+========================+======================+=========================+
| :icon:`fi-unlock`      | Make available       | :doc:`../status`        |
+------------------------+----------------------+-------------------------+
| :icon:`fi-lock`        | Make unavailable     | :doc:`../status`        |
+------------------------+----------------------+-------------------------+
|                        | Archive              | :doc:`../status`        |
+------------------------+----------------------+-------------------------+
| :icon:`fi-pencil`      | Edit                 | :doc:`edit`             |
+------------------------+----------------------+-------------------------+
| :icon:`fi-clock`       | Edit Timed Actions   | :doc:`../timed_actions` |
+------------------------+----------------------+-------------------------+
| :icon:`fi-torsos-all`  | Users                | :doc:`users`            |
+------------------------+----------------------+-------------------------+
| :icon:`fi-key`         | Edit Access Settings | :doc:`access_settings`  |
+------------------------+----------------------+-------------------------+
| :icon:`fi-plus`        | Add Part             | :doc:`../part/index`    |
+------------------------+----------------------+-------------------------+
|                        | Add Asset            | :doc:`../asset/new`     |
+------------------------+----------------------+-------------------------+
|                        | Import               | :doc:`../import_export` |
+------------------------+----------------------+-------------------------+
|                        | Export               | :doc:`../import_export` |
+------------------------+----------------------+-------------------------+
|                        | Download             | :doc:`../download`      |
+------------------------+----------------------+-------------------------+
| :icon:`fi-trash`       | Delete               | :doc:`delete`           |
+------------------------+----------------------+-------------------------+

You can find further detail here:

.. toctree::
   :maxdepth: 2

   new
   edit
   delete
   access_settings
   users
