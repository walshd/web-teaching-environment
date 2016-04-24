Including Assets
----------------

To include :doc:`assets<../asset/index>` in your content, simply type
``:asset:`filename``` and the asset with the given filename will be included at
that point in the content.

If the asset is an image, then the image will be shown at this point in the
content. If the asset is any other type of file, then a link from which the user
can download the asset will be shown.

For example the following inclusion of an image:

.. sourcecode:: rest

  :asset:`sample.jpg`
  
will be displayed as

.. rst-class:: rest-render-sample

  .. image:: sample.jpg

Alternatively, if you link to another type of file, for example a PDF file, then the
following ReST:

.. sourcecode:: rest

  Access the :asset:`notes.pdf`.

will be displayed as

.. rst-class:: rest-render-sample

  Access the :text_link:`Notes`.
  
By default the link's text is taken from the asset's title. If you want to override
this, first provide the link text and then the asset filename in angle brackets:

.. sourcecode:: rest

  Access the :asset:`notes by clicking here <notes.pdf>`.

will be displayed as

.. rst-class:: rest-render-sample

  Access the :text_link:`notes by clicking here`.

Searching for Assets
^^^^^^^^^^^^^^^^^^^^

If you are unsure what the exact asset filename is, then you can also search for the
asset by clicking on the :text_link:`Assets` link on the left in the toolbox. This
will show a search box. Either type the title or filename of the asset you are looking
for into the search box and click on the :primary_btn:`Search` button, or leave the
search box empty and click on the :primary_btn:`Search` button to see all assets.

A list of all assets matching your search terms or of all assets will be shown below
the search box. Click on the asset's name to have it inserted into your content at the
current cursor position.
