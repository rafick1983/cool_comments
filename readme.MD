To store the history I used a DB trigger, because the project is small. It works faster than an additional query to
add a record to the history table. For big projects I usually use django-revertion app. It enables to recover
removed objects, speed up development, but slower than triggers. The trigger is updated by the post migrate
signal, because it eases development - I don't need to create a migration every time I need to change the trigger.

To send push notifications I used django-push-notifications app.

Comments shouldn't be removed as the task requires, because of lose of comment's history. Instead of this the
is_removed field is used.

I used celery tasks to export data and to send push notification. It can take long and the worker eventually will
stop respond without async tasks.

For exporting data I used django built-in serializer. It's the way to do fast serialization of a queryset out of the
box. Also I'd use django-import-export app for other file formats.
Also possible to implement a custom export classes. A class with description of fields and a set of adapters for
various file formats, but why to reinvent the wheel.

Unit tests are put into a single file because the project is small. In a big project the unit tests should be written
for each module each in a separate file and cover as much code as possible.

For authentication I used djangorestframework-jwt. I used it in my recent project and decided why not to use it here.

Also I exposed an URL for documentation.
