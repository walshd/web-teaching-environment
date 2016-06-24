Editor
======

The editor consists of three parts. In the centre is the main text editor itself. The left
consists of a toolbox that provides support for the editor (:doc:`asset` & :doc:`crossref`).
On the right-hand side is a live preview of the editor content as it will appear to the learner.

The text editor uses ReStructured Text as its basic format (:doc:`rst-primer`), augmented with funcationality for
formatting :doc:`sourcecode<sourcecode>`, :doc:`assets<asset>` (see also :doc:`../asset/index`),
:doc:`cross-references<crossref>`, and :doc:`videos<video>`. 

As you type into the text editor, the added text is automatically centred in the viewer. To highlight the
preview text for a line in the editor, you can also press the ``Ctrl`` key and then click on the line
to highlight. You can also click on any element in the viewer to go to that line in the text editor
(some guesswork is involved here, so it might be off by a few lines).

You can find more detail here:

.. toctree::
   :maxdepth: 1

   rst-primer
   sourcecode
   asset
   crossref
   video
   quiz
   show-hide
