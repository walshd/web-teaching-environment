HTML Editor Sections
--------------------

HTML Editor Sections combine the tutorial text, an HTML/CSS/JavaScript editor, and
an HTML viewer into a single interface. These are laid out like this:

+----------+-----------+
| Tutorial | Workspace |
|          +-----------+
|          | Viewer    |
+----------+-----------+

Tutorial
^^^^^^^^

On the left the *tutorial* contains the actual text of the tutorial that you
are following. At the top and bottom of the *tutorial* you will find the
:text_link:`Previous page` and :text_link:`Next page` links that allow you to
move forwards and back through the tutorial's content. Additionally you can
use the drop-down list to quickly jump between pages.

Workspace
^^^^^^^^^

Each tutorial will consist of one or more files that you will work on as you
follow the tutorial. These files will be shown in the *workspace* area as a series
of tabs. You can switch between the files by clicking on the tab with the
filename of the file you wish to edit.

Whenever you make a change to one of the files, the change is automatically
saved after a few seconds of inactivity. If you do not want to wait that long,
you can click on the :icon:`fi-save` icon. To indicate that there are unsaved
changes the tab will turn red when you make a change and green after the change
has been saved.

All the work you do is saved on the server. This means that if you leave the
tutorial and come back to it at a later point, the content of the files will
be exactly as you left them.

Downloading files
"""""""""""""""""

If you want to download the files' content for working on them offline, you
can do that by clicking on the :icon:`fi-list` icon in the top-right corner.
Then select the :dropdown_link:`Download the Workspace` item. This will generate
a ZIP file, which contains all the files in the *workspace*.

Alternatively, if you want to download a single file, click on the :icon:`fi-list` icon
on the tab of the file that you want to download. Then, from the drop-down menu
select the :dropdown_link:`Download` option to download that one file.

Discarding changes
""""""""""""""""""

Sometimes you might want to discard some or all of the changes that you have
made to one or more files and re-start with the initial file contents. To
discard all changes, click on the :icon:`fi-list` icon in the top-right corner and from
the drop-down menu select :dropdown_link:`Discard all Changes`. This action cannot be undone,
so you will be asked to confirm that you want to discard all changes. If you
confirm that you want to discard all changes, the page will re-load and the
files will have been reset to their initial state.

If you want to discard the changes from a single file, click on the :icon:`fi-list` icon
in the tab of the file that you want to reset. Then select the
:dropdown_link:`Discard Changes` option from the drop-down menu. The action cannot be undone, so you
will be asked to confirm that you want to discard the changes to that file. If
you confirm that you want to discard the changes, then the page will re-load
and the file will have been reset to its initial state. All other files will
retain the modifications you have made. 

Viewer
^^^^^^

On the right-hand side in the bottom half is the page *viewer*, which shows the
HTML page's content. You can interact with this as you would with any other
HTML page and it allows you to try out what your HTML code would look like in
practice. The content of the *viewer* will automatically re-load whenever you
make a change to any of the files in the *workspace*.

View in new tab / window
""""""""""""""""""""""""

While the *viewer* works like a normal web-page, it is somewhat restricted in
its size. If you want to see what your HTML would look like in its own tab or
window, then click on the :icon:`fi-list` icon in the top-right corner of the *viewer*.
From the drop-down menu, select the :dropdown_link:`Open in new Tab/Window` option and the
page will be opened in a new tab or window (which one depends on your browser's
settings).

.. note:: The content of the new tab or window will **not** be updated
   automatically if you make any changes in the *workspace*. If you make
   changes in the *workspace* then you need to manually re-load the page in
   the new tab or window for those changes to become visible.
   
Quizzes
^^^^^^^

The Web Teaching Environment allows the tutor to set small quizzes. To answer the quiz,
simply select the correct answers and then click on the :primary_btn:`Check Answers` button.
You will immediately be shown which answers you got right and which are wrong. You can re-try
any questions that you did not get right.
