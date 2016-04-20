Introduction to ReStructured Text
---------------------------------

The basic idea behind ReStructured Text (ReST) is to have a text format where the source text gives
a visual indication of what the rendered text will look like. This page will give you a quick introduction
to ReST. For more details consult http://www.sphinx-doc.org/en/stable/rest.html. The content editor
gives you an immediate display of what your ReST will look like, so the easiest way to get comfortable
with ReST is just to try it out in the editor (rest assured you cannot break anything).

| Quick links:
| `Plain Text`_
| `Structuring Text`_
| `Highlighting Text`_
| `Lists`_
| `Tables`_

Plain Text
^^^^^^^^^^

The basic structure in ReST is the paragraph, which is simply a chunk of text separated from all other text
by an empty line. You can split the text of a paragraph over multiple lines (as long as there is no empty
line), but you **must** ensure that each line is indented by the same amount of white-space on the left.
For example the following ReST

.. sourcecode:: rest

  This is a basic paragraph that will
  be shown as one long piece of text.

will be displayed as

.. rst-class:: rest-render-sample
 
   This is a basic paragraph that will
   be shown as one long piece of text.
   
By default the any line-breaks you put in your text will simply be treated as spaces. If you want your
line-breaks to be respected, then you need to prefix each line with ``|``. For example the following ReST 

.. sourcecode:: rest

  | This text will be shown
  | with exactly this layout
  | and all line-breaks included.

will be displayed as

.. rst-class:: rest-render-sample
 
   | This text will be shown
   | with exactly this layout
   | and all line-breaks included.

If you want your text to be shown as a quote, then simply indent the text with more white-space than the
preceeding paragraph. For example the following ReST

.. sourcecode:: rest

  This is the paragraph preceeding the quote.
  
    This is the quoted text.
    
    -- By somebody famous

will be displayed as

.. rst-class:: rest-render-sample
 
   This is the paragraph preceeding the quote.
  
       This is the quoted text.
    
       -- By somebody famous

Structuring Text
^^^^^^^^^^^^^^^^

To add headings to your text and structure your text in that way, simply add a line of the same character
under your heading. It doesn't matter which, but ``=``, ``-``, ``#``, and ``+`` are generally used as they
are visually distinctive. The length of the line must be exactly the same as the length of text that is to
be the heading. To distinguish different heading levels, simply use a different character. ReST will automatically
figure out which heading is a sub-heading of which other heading. For example the following ReST creates a two-level
structure:

.. sourcecode:: rest

  Heading 1
  =========
  
  Heading 1.1
  -----------
  
  Heading 1.2
  -----------
  
  Heading 2
  =========

Because both "Heading 1" and "Heading 2" are underlined with ``=``, ReST knows that they are the same level.
The same goes for "Heading 1.1" and "Heading 1.2", but because they use a different character, ReST knows that
they are the next level of heading.

.. note::

  If the first line in your content is a heading, then this will not be displayed, unless you have
  multiple heading levels.

Highlighting Text
^^^^^^^^^^^^^^^^^

You can highlight text using italics, bold, or tele-type. To highlight text using italics, surround the word(s)
you wish to highlight using a single asterisk ``*``. To highlight text using bold font, surround the word(s)
you wish to highlight using a double asterisk ``**``. To use tele-type, surround the word(s) with a double
backtick ``````.

.. sourcecode:: rest

  This is *italic*, **bold**, and ``tele-type``.

Three things must be observed when highlighting:

* You **must** have either white-space or punctiation directly before and after the text to highlight. You cannot
  highlight within part of a word. ``in*correct*`` will give an error.
* The word(s) to highlight **must** start directly after the opening marker and end directly before the closing marker.
  You cannot highlight white-space. ``* fails*`` will give an error.
* You cannot nest highlighting. ````**bold tele-type**```` will give an error.

Lists
^^^^^

ReST supports three types of lists: bullet lists, enumerated lists, and definition lists.

To create a bullet list, start each line that is an item in the list with a single asterisk ``*``. For example the following ReST

.. sourcecode:: rest

  * Item
  * Item
  * Item
  
will be displayed as

.. rst-class:: rest-render-sample
 
   * Item
   * Item
   * Item

To create an enumerated list, start each line that is an item in the list with a single ``#.*``. For example the following ReST

.. sourcecode:: rest

  #. Item 1
  #. Item 2
  #. Item 3
  
will be displayed as

.. rst-class:: rest-render-sample
 
   #. Item 1
   #. Item 2
   #. Item 3

To create a definition list, consisting of pairs of definition term and the definition text, simply indent the paragraph with
the definition text. For example the following ReST

.. sourcecode:: rest

  Item 1
    This is the definition for Item 1.
  Item 2
    This is the definition for Item 2.

will be displayed as

.. rst-class:: rest-render-sample
 
   Item 1
     This is the definition for Item 1.
   Item 2
     This is the definition for Item 2.

You can nest lists, you just need to ensure that the nested list is separated from its parent item and from the next item
using an empty line and that the indentation of the nested list lines up with where the text for its parent
list item starts. For example the following ReST 

.. sourcecode:: rest

  #. Item 1
  
     #. Item 1.1
     #. Item 1.2
     
  #. Item 2
  #. Item 3
  
     #. Item 3.1
     #. Item 3.2

will be displayed as

.. rst-class:: rest-render-sample
 
  #. Item 1

     #. Item 1.1
     #. Item 1.2
   
  #. Item 2
  #. Item 3

     #. Item 3.1
     #. Item 3.2
     
Tables
^^^^^^

Tables are the most complex structure in ReST, as you need to "draw" them in text. The following ReST
demonstrates a simple, two-column table:

.. sourcecode:: rest

  +------------------+------------------+
  | Column 1 Heading | Column 2 Heading |
  +==================+==================+
  | Row 1 - Column 1 | Row 1 - Column 2 |
  +------------------+------------------+
  | Row 2 - Column 1 | Row 2 - Column 2 |
  +------------------+------------------+
  | Row 3 - Column 1 | Row 3 - Column 2 |
  +------------------+------------------+

The table would be displayed as

.. rst-class:: rest-render-sample

   +------------------+--------------------+
   | Column 1 Heading | Column 2 Heading   |
   +==================+====================+
   | Row 1 - Column 1 | Row 1 - Column 2   |
   +------------------+--------------------+
   | Row 2 - Column 1 spanning two columns |
   +------------------+--------------------+
   | Row 3 - Column 1 | Row 3 - Column 2   |
   +------------------+--------------------+

It is important that any table you create follows the following rules:

* Each column must be as wide as the widest cell in that column. Pad the other columns with white-space.
* Rows are separated using ``-``
* Columns are separated using ``|``
* Where a row and column intersect you must place a ``+``
* You must have one space between the cell start and end marker ``|``
* To create a header row for the table, separate that row from the rest of the table using ``=`` instead of ``-``

There are on-line tools to help you generate the ReST for any content you have. Search for "rest table generator".
