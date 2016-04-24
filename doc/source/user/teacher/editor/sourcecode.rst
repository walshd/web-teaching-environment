Highlighting Sourcecode
-----------------------

The WTE comes with sophisticated source-code highlighting as part of the
content editor (using the `pygments`_ library). Creating a highlighted source-code
block is very simple. You start a block of code with the ``.. sourcecode::``
directive. After the ``::`` you must provide a blank space and then the type of
source-code that your block will contain. After the directive, you **must**
have one empty line and then the source-code must be indented by at least two
spaces.

For example the following ReST will create syntax highlighting for HTML:

.. sourcecode:: rest

  .. sourcecode:: html
  
    <html>
      <head>
        <title>Testing</title>
      </head>
      <body>
        <h1>Body</h1>
      </body>
    </html>

which will be displayed as:

.. sourcecode:: html
  
  <html>
    <head>
      <title>Testing</title>
    </head>
    <body>
      <h1>Body</h1>
    </body>
  </html>

You can find the full list of available languages for syntax highlighting
`here`_.

Options
^^^^^^^

You can pass options to the source-code directive in order to modify how
the source-code is highlighted. Options must follow directly after the
``.. sourcecode::`` directive and must be separated from the highlighted
source-code by an empty line.

* ``:filename: XXX`` - Displays a file-name in the top-right corner of the
  source-code block. Replace the ``XXX`` with the actual file-name to show
* ``:linenos: X`` - Displays line-numbers. Replace the ``X`` with the
  number you want to start enumerating at

The following example shows the same HTML being highlighted, but with the
inclusion of a filename ("index.html") and with line numbers starting at
1.

.. sourcecode:: rest

  .. sourcecode:: html
    :filename: index.html
    :linenos: 1
  
    <html>
      <head>
        <title>Testing</title>
      </head>
      <body>
        <h1>Body</h1>
      </body>
    </html>


.. _pygments: http://pygments.org/
.. _here: http://pygments.org/docs/lexers/
