Allowing the User to Show and Hide Content
------------------------------------------

The WTE allows you to mark blocks of content as "optional" in that they can be shown
and hidden by the user. To create such an optional block, start it with ``.. show-hide::``
and then add whatever content you wish to add.

.. sourcecode:: rest

  .. show-hide::
  
    This paragraph is initially visible, but can be hidden by the user.

By default blocks are initially visible, but can be hidden. If you want the block to
initially be hidden, add the ``:initial: hidden`` option:

.. sourcecode:: rest

  .. show-hide::
    :initial: hidden
  
    This paragraph is initially hidden, but can be shown by the user.

You can also add an arbitrary title to the block using the ``:title:`` option:

.. sourcecode:: rest

  .. show-hide::
    :initial: hidden
    :title: Click on the plus icon to show the answer
    
    The answer to the question was 42.

The title will always be visible, so you can use it to let the user know that they there
is content to be shown or for anything else you wish to let the user know.

You can put any other content in a ``show-hide`` block. The next example has a nested
``sourcecode`` block:

.. sourcecode:: rest

  .. show-hide::
    :initial: hidden
    :title: Your code should now look like this:
    
    .. sourcecode:: HTML
    
      <html>
        <head>
        </head>
        <body>
        </body>
      </html>
