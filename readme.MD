I decided not to use django-revertion app to store the history. Use of a db trigger works much faster than a bunch
of queries spawned by django-reversion. Also the task doesn't require restoration of the removed records and requires
to implement history only for one table.
Comments shouldn't be removed as the task requires, because of lose of comment's history. Instead of this the is_removed
field is used.
