Instructions for the Automatically Updated Game List
====================================================

This page contains instructions for posters to influence how their post shows
up on the [game list][1].

[1]: http://helixmod.blogspot.com/2013/10/game-list-automatically-updated.html

Post Titles
-----------
In general you should just use the name of the game you are fixing in the
title, but the script can cope with some additional notes after the title, such
as the examples below. The original title can be displayed by hovering the
mouse over the link for a few seconds.

"Awesome Game _(DirectX 9 only)_" --> "Awesome Game [DX9]"

"Kickass Game _- 3D Vision Fix_" --> "Kickass Game"

"Sweet Game _(NEW VERSION)_" --> "Sweet Game"

"Super Cool Game _by DarkStarSword_" --> "Super Cool Game"

"Nice Game _(UPDATED 10/14)_" --> "Nice Game"

The script can cope with some variations and combinations of these - if you
want to use a title that is not getting transformed properly send me a note and
I'll adapt the regular expressions or add an override.

In the event that multiple posts exist for the same game (see below), these
transformations will not be performed on the individual posts to allow the
different posts to more easily be distinguished. The group heading will still
have the transformations applied.

Grouping Posts for the Same Game
--------------------------------
If you make a new post for a fix to a game that is already in the list, try to
give it the same title and spelling as the original game and the script will
automatically group them together.

In some cases you may not want to use the existing spelling for whatever reason
(e.g. "TESV: Skyrim" vs. "The Elder Scrolls V: Skyrim") - in that case send me
a note and I'll add a pattern to the script so it knows to treat them as the
same game.

The published date according to Blogger will be added next to each version with
the most recent at the top. The group heading will also link to the most
recent post. Note that Blogger allows you to set a custom published date if you
wanted to override this order (be aware that doing so will also affect where
your post appears on the main site).

Guide and Misc Posts
--------------------
Add a "guide" or "misc" label to your post in Blogger and it will automatically
show up under the correct section.

Incomplete Fixes, Disabled Effects, etc.
----------------------------------------
To indicate that a game has only been partially fixed by disabling effects or
is otherwise rated less than excellent, add a "disabled" label to the post.
This will automatically tag the game with [Disabled Effects] in the list.

Web Developers
--------------
If you want to adapt and use the script for your own purposes feel free to do
so. It is released under the terms of the [General Public Licence version
3 (or later)][2], but I'm flexible with licensing so if that doesn't suit you
please get in touch.

You can find the source for the script [on github][3].

You will need to get your own [API key][4] to use the Blogger v3 API.

[2]: https://www.gnu.org/licenses/gpl.html
[3]: https://github.com/DarkStarSword/3d-fixes/tree/master/__game_list__
[4]: https://developers.google.com/blogger/docs/3.0/using#APIKey
