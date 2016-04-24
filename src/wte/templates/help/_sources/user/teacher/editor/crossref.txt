Referincing other Modules/Parts/Pages
-------------------------------------

To reference another :doc:`module<../module/index>`, :doc:`part<../part/index>`, or
:doc:`page<../page/index>` simply type ``:crossref:`XX``` and a link to the module,
part, or page will be shown at that point. Replace the XX with the identifier
of the module, part, or page you wish to reference. You can find the identifier by
looking at the URL for that module, part, or page and the identifier is the number
at the end of the URL.

The following ReST

.. sourcecode:: rest

  See :crossref:`4`.
  
will be displayed as

.. rst-class:: rest-render-sample

  See :text_link:`Title of the Module`

As with :doc:`assets<asset>`, by default the title of the link is the title of the
module, part, or page that the link is referencing. As with assets you can put
the identifier in angle brackets and add a custom link text:

.. sourcecode:: rest

  See :crossref:`here<4>`

will be displayed as

.. rst-class:: rest-render-sample

  See :text_link:`here`

Searching for Modules/Parts/Pages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Easier than finding the identifier manually is to use the cross-reference search in the
toolbox on the left. Click on the :text_link:`Cross-references` to show the cross-reference
search box. Type the title of the module/part/page you want to reference into the search
box and then click on the :primary_btn:`Search` button. A list of all matching modules/parts/pages
will be shown. Click on the module/part/page title that you want to reference and the
correct cross-reference ReST will be added into the content at the current cursor position.
