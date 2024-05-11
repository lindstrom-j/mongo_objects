Sample Application
=============================

The :mod:`mongo_objects`
`source code <https://github.com/lindstrom-j/mongo_objects>`_
as well as the source distribution package include a sample Flask
application that demonstrates many common usage patterns.

Starting The Sample Application
-------------------------------

The :file:`sample/run-sample-app` shell script makes the following
assumptions:

    * The :program:`bash` shell is available at :file:`/bin/bash`.
    * :program:`python3` and :program:`pip3` are available on the path
      with access to the Internet.
    * MongoDB is installed as :program:`mongod` but not running.
    * The :file:`sample` directory is writable.

The script performs the following actions:

    * Creates a Python 3 virtual environment in the :file:`sample/venv` directory
      and installs the required modules as listed in :file:`sample/requirements.txt`.
    * Creates a :file:`sample/db` directory and starts :program:`mongod` in
      unsecured mode against that directory. To override this step and use a different
      MongoDB instance, provide the connect string in the :envvar:`MONGO_CONNECT_URI`
      environment variable.
    * Starts :program:`flask` running the :mod:`sample/mongo_objects_sample.py`
      sample application module
    * Shuts down :program:`mongod` when :program:`flask` terminates.


Press :kbd:`Control-C` to terminate :program:`flask` and end the script. For example::

    % sample/run-sample-app
    created new virtual environment for mongo_objects sample app
    activated mongo_objects sample app virtual environment
    Collecting Flask
    Collecting Flask-PyMongo
    Collecting Flask-WTF
    Collecting MarkupSafe
    Collecting pymongo
    Collecting WTForms
    Collecting Werkzeug>=3.0.0 (from Flask)
    Collecting Jinja2>=3.1.2 (from Flask)
    Collecting itsdangerous>=2.1.2 (from Flask)
    Collecting click>=8.1.3 (from Flask)
    Collecting blinker>=1.6.2 (from Flask)
    Collecting dnspython<3.0.0,>=1.16.0 (from pymongo)
    ...
    Installing collected packages: MarkupSafe, itsdangerous, dnspython, click, blinker, WTForms, Werkzeug, pymongo, Jinja2, Flask, Flask-WTF, Flask-PyMongo
    Successfully installed Flask-3.0.3 Flask-PyMongo-2.3.0 Flask-WTF-1.2.1 Jinja2-3.1.4 MarkupSafe-2.1.5 WTForms-3.1.2 Werkzeug-3.0.3 blinker-1.8.2 click-8.1.7 dnspython-2.6.1 itsdangerous-2.2.0 pymongo-4.7.2
    installed required modules for mongo_objects sample app virtual environment
    Started MongoDB PID 66702
    * Serving Flask app 'mongo_objects_sample'
    * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    * Running on http://127.0.0.1:5000
    Press CTRL+C to quit
    * Restarting with stat
    * Debugger is active!
    * Debugger PIN: 942-992-575
    ^CStopped MongoDB


Application Overview
--------------------

The sample Flask application manages ticket sales to imaginary events.

There are two modes. In *admin* mode, you manage events while in *customer*
mode you may view events and "purchase" tickets. Use the dropdown menu in
the navigation bar to switch between modes.

The data for the entire application is stored in a single MongoDB collection
named ``events`` in the ``mongo_objects_sample`` database.
Each event including related information like venue location, types of tickets
and tickets sold is stored as a single MongoDB document.

We recommend installing the `MongoDB Compass tool <https://www.mongodb.com/try/download/compass>`_
to inspect the documents managed by :mod:`mongo_objects`.


MongoUserDict: Scheduling An Event
----------------------------------

Events are stored as :class:`MongoUserDict` subclasses called :class:`Event`. Use admin
mode to create your first event as follows:

.. image:: _static/create-event.png
    :align: center
    :width: 80%


Now use Compass to view the contents of the ``events`` collection.
There should be one document similar to the following::

    {
        "_id": "663c54bbeba88ab288f3bd3d",
        "name": "End Of The Century Party",
        "description": "This will be even more fun than last time!",
        "eventDate": "2099-12-31T00:00:00.000Z",
        "_updated": "2024-05-09T04:44:43.030Z",
        "_created": "2024-05-09T04:44:43.030Z"
    }

This is a typical MongoDB document dictionary, although you'll notice
:class:`MongoUserDict` helpfully added `_created` and `_updated`
timestamps to the document when it was saved.

If you look at the event details page in the sample app, you'll see
a URL similar to ``http://127.0.0.1:5000/admin-event-detail/663c54bbeba88ab288f3bd3d``.
The unique number in the URL is just the MongoDB ObjectId.
The :meth:`MongoUserDict.id` and :meth:`MongoUserDict.load_by_id`
methods to make it easy to locate
documents by their ObjectId.

Because events are actually represented using a :class:`MongoUserDict` subclass
named :class:`Event`, we have added our own methods to assist with the event
workflow. :meth:`.displayDate` provides consistent date formatting while
:meth:`.isSoldOut` provides a single calculation for ticket availability.

By passing an :class:`Event` object to another function or even to a Jinja
template, not only the event data but also all these methods are available
as well.


MongoSingleProxy: Adding A Venue
--------------------------------

The venue location is stored as a simple subdocument dictionary within the
parent event document. We use a :class:`MongoSingleProxy` subclass named
:class:`Venue` to manage this data structure.

Use the admin mode to add venue information to the event as follows:

.. image:: _static/add-venue.png
    :align: center
    :width: 80%

Check the MongoDB document with Compass::

    {
        "_id": "663c54bbeba88ab288f3bd3d",
        "name": "End Of The Century Party",
        "description": "This will be even more fun than last time!",
        "eventDate": "2099-12-31T00:00:00.000Z",
        "_updated": "2024-05-09T07:07:18.207Z",
        "_created": "2024-05-09T04:44:43.030Z",
        "venue": {
            "name": "The Grand Theater",
            "address": "123 Grand Avenue",
            "phone": "123 456 7890"
        }
    }

You'll notice that the *_updated* field has indeed been updated
to reflect the last document save time.

There's also a new *venue* dictionary within the main document.
This represents the :class:`Venue` proxy object. The *venue* name
came from the *container_name* in the class definition.

If there are any venue-specific methods, we could include them in
the :class:`Venue` class instead of cluttering up :class:`Event`.

Since the data for each proxy object only exists in the parent
MongoDB document, the parent document must be loaded before the
proxy is available. We've included a helpful :meth:`Event.getVenue` method
to return the :class:`Venue` proxy object from a :class:`Event`
already loaded into memory.

Each proxy object has a unique ID that includes the parent document
ObjectId. There's an :meth:`Event.loadVenueById` class method that
parses the venue ID, loads the correct :class:`Event` document and
returns the appropriate :class:`Venue` proxy object.


MongoDictProxy: Defining Ticket Types
-------------------------------------

For "one-to-many" relationships, SQL statements require table joins
to connect the information. In No-SQL databases like MongoDB, it
is more efficient to simply include the "many" items as multiple
subdocuments within the same primary document.

The :class:`MongoDictProxy` class manages a single dictionary container
that in turn holds multiple subdocument dictionaries of the same type.

In our sample app, for example, each event may have multiple ticket
types for sale. Instead of a separate "ticket type" collection, all
ticket types are included as :class:`TicketType` subdocuments
within the main :class:`Event` object.

To illustrate this functionality, use the admin mode to add three ticket types
to our event.

VIP tickets:

.. image:: _static/add-ticket-type-1.png
    :align: center
    :width: 80%

General admission:

.. image:: _static/add-ticket-type-2.png
    :align: center
    :width: 80%

Discounted student tickets:

.. image:: _static/add-ticket-type-3.png
    :align: center
    :width: 80%

Use MongoDB Compass to check the document content::

    {
        "_id": "663c54bbeba88ab288f3bd3d",
        "name": "End Of The Century Party",
        "description": "This will be even more fun than last time!",
        "eventDate": "2099-12-31T00:00:00.000Z",
        "_updated": "2024-05-09T07:21:59.145Z",
        "_created": "2024-05-09T04:44:43.030Z",
        "venue": {
            "name": "The Grand Theater",
            "address": "123 Grand Avenue",
            "phone": "123 456 7890"
        },
        "_last_unique_integer": 3,
        "ticketTypes": {
        "1": {
            "name": "VIP Ticket",
            "description": "The best seats in the house!",
            "cost": 200,
            "ticketsTotal": 10
        },
        "2": {
            "name": "General Admission",
            "description": "Everyone is welcome!",
            "cost": 100,
            "ticketsTotal": 100
        },
        "3": {
            "name": "Student Ticket",
            "description": "Take a break from the books",
            "cost": 50,
            "ticketsTotal": 50
        }
        }
    }

The biggest change is the new *ticketTypes* dictionary. The name
came from the *container_name* attribute of the :class:`TicketType`
class.

The *ticketTypes* dictionary itself contains three dictionaries,
one for each of our :class:`TicketType` proxy objects. The keys
for each dictionary were auto-assigned by :class:`MongoDictProxy`
and have nothing to do with the content of the subdocument. Even
if the content changes, the key remains the same.

A *_last_unique_integer* value has also been added automatically to track
on a per-document basis the last proxy ID value that was issued.

Of course, the *_updated* timestamp was also updated.

If you use the admin mode to explore ticket type details, you'll
see a URL like ``http://127.0.0.1:5000/admin-ticket-detail/663c54bbeba88ab288f3bd3dg1``.
Each proxy object has a unique ID consisting of the document ObjectId plus the
proxy subdocument key. ``g`` is used as a URL-safe, non-hexidecimal separator.

Each proxy object provides a :meth:`id` method that constructs the unique ID.
:class:`MongoUserDict` provides :meth:`.load_proxy_by_id` to parse a proxy object
ID, load the correct parent document and return the appropriate subdocument
object. In fact, our :class:`Event` class method :meth:`.loadTicketTypeById`
just calls :meth:`.load_proxy_by_id` to locate and return :class:`TicketType` objects.

Once an :class:`Event` object is loaded, :meth:`.getTicketTypes` has been
included to call :meth:`MongoUserDict.get_proxies` and return a list
of all :class:`TicketType` proxies. The method :meth:`.getTicketType` can be called
to create a proxy for a single ticket type based on the key.


MongoListProxy: Selling Tickets
-------------------------------

Another pattern for saving "one-to-many" subdocuments in the
parent document is to use a list as the container. :class:`MongoListProxy`
supports using lists as a container object.

Our sample app uses a :class:`MongoListProxy` subclass called
:class:`Ticket` to represent each ticket sold.

Use the customer mode of the sample app to purchase a VIP ticket
to our end-of-the-century party.

.. image:: _static/purchase-ticket.png
    :align: center
    :width: 80%

Let's look at the actual data with Compass::

    {
        "_id": "663c54bbeba88ab288f3bd3d",
        "name": "End Of The Century Party",
        "description": "This will be even more fun than last time!",
        "eventDate": "2099-12-31T00:00:00.000Z",
        "_updated": "2024-05-09T08:56:25.171Z",
        "_created": "2024-05-09T04:44:43.030Z",
        "venue": {
            "name": "The Grand Theater",
            "address": "123 Grand Avenue",
            "phone": "123 456 7890"
        },
        "_last_unique_integer": 4,
        "ticketTypes": {
            "1": {
                "name": "VIP Ticket",
                "description": "The best seats in the house!",
                "cost": 200,
                "ticketsTotal": 10
            },
            "2": {
                "name": "General Admission",
                "description": "Everyone is welcome!",
                "cost": 100,
                "ticketsTotal": 100
            },
            "3": {
                "name": "Student Ticket",
                "description": "Take a break from the books",
                "cost": 50,
                "ticketsTotal": 50
            }
        },
        "tickets": [
            {
            "name": "Fred",
            "ticketTypeKey": "1",
            "issued": "2024-05-09T08:56:25.171Z",
            "_sdkey": "4"
            }
        ]
    }

The major change is the new *tickets* list containing a single
subdocument dictionary representing the ticket we just purchased
for Fred.

Each :class:`MongoDictProxy` and :class:`MongoListProxy` proxy object
is tracked by a key. Since lists don't natively use keys, a *_sdkey*
(short for subdocument key) value has been added to the dictionary
in the *tickets* list.

This key value is used when constructing the full proxy ID. In fact,
if you switch back to admin mode and look at the VIP tickets detail
page, you'll see that Fred's ticket number is just the proxy ID.

.. image:: _static/vip-ticket-detail-1.png
    :align: center
    :width: 80%

The key is also used to track the subdocument dictionary within the
list. If the list is modified, :class:`MongoListProxy` will use the
key to locate the new index of the subdocument dictionary in the list.

Because a new key has been issued, *_last_unique_integer* has been
updated as well as the *_updated* timestamp.


PolymorphicMongoDictProxy: Ticket Benefits
------------------------------------------

It to sometimes convenient to store similar but not identical types
of information within the same container. All :mod:`mongo_objects`
proxy classes have polymorphic versions that will return different
objects from the same container based on an identifier.

Our sample app uses a tree of :class:`PolymorphicMongoDictProxy` subclasses
to track the benefits associated with each ticket type. Some benefits
are considered intangible features like a front row seat or unobstructed view.
Other benefits are tangible gifts like free popcorn or a gift bag.

This data structure is defined as follows::

    class Benefit( mongo_objects.PolymorphicMongoListProxy ):
        container_name = 'benefits'
        proxy_subclass_map = {}

    class Feature( Benefit ):
        proxy_subclass_key = 'ft'

    class Gift( Benefit ):
        proxy_subclass_key = 'gt'

The :class:`Benefit` base class defines the *container_name* that the
two subclasses will share. The :class:`Feature` and :class:`Gift`
subclasses each define a unique *proxy_subclass_key* value that
:class:`PolymorphicMongoDictProxy` uses to decide which class to
instantiate.

Use admin mode to add a feature to the VIP ticket type:

.. image:: _static/add-feature.png
    :align: center
    :width: 80%


Now add a gift to the VIP ticket type:

.. image:: _static/add-gift.png
    :align: center
    :width: 80%


Let's look at the data::

    {
        "_id": "663c54bbeba88ab288f3bd3d",
        "name": "End Of The Century Party",
        "description": "This will be even more fun than last time!",
        "eventDate": "2099-12-31T00:00:00.000Z",
        "_updated": "2024-05-09T09:38:22.027Z",
        "_created": "2024-05-09T04:44:43.030Z",
        "venue": {
            "name": "The Grand Theater",
            "address": "123 Grand Avenue",
            "phone": "123 456 7890"
        },
        "_last_unique_integer": 6,
        "ticketTypes": {
        "1": {
            "name": "VIP Ticket",
            "description": "The best seats in the house!",
            "cost": 200,
            "ticketsTotal": 10,
            "benefits": [
                {
                "name": "Front Row Seat",
                "description": "Guaranteed unobstructed view.",
                "_psckey": "ft",
                "_sdkey": "5"
                },
                {
                "name": "Panda Plushie",
                "description": "Cute and cuddly",
                "value": 20,
                "_psckey": "gt",
                "_sdkey": "6"
                }
            ]
        },
        "2": {
            "name": "General Admission",
            "description": "Everyone is welcome!",
            "cost": 100,
            "ticketsTotal": 100
        },
        "3": {
            "name": "Student Ticket",
            "description": "Take a break from the books",
            "cost": 50,
            "ticketsTotal": 50
        }
        },
        "tickets": [
            {
            "name": "Fred",
            "ticketTypeKey": "1",
            "issued": "2024-05-09T08:56:25.171Z",
            "_sdkey": "4"
            }
        ]
    }

The "VIP Ticket" subdocument in the *tickets* dictionary now has a *benefits*
list containing two subdocuments of its own. :mod:`mongo_objects` proxy objects
support nesting as many levels as you like and in any order. In this case,
a :class:`MongoListProxy` is nested within a :class:`MongoDictProxy`.

The method :meth:`MongoUserDict.id` builds IDs for nested proxies and the
class method :meth:`MongoUserDict.load_proxy_by_id` loads nested proxies.
This functionality is used to implement :meth:`Event.loadBenefitById`.

If you update the Front Row Seat feature added above, you'll see an example
of a nested proxy ID in the URL, for example,
``http://127.0.0.1:5000/admin-update-feature/663c54bbeba88ab288f3bd3dg1g5``.

Notice that each subdocument has a *_psckey* value that matches the
*proxy_subclass_key* value of the :class:`Benefit` subclass to be
instantiated for that particular subdocument.

There's an important distinction to observe when calling :meth:`get_proxies`
for polymorphic proxies:

    * If you call the base class, you will get all proxies in the container,
      each with the correct class. In the example above ``Benefit.get_proxies()``
      will return a list with two objects, one :class:`Feature` and one
      :class:`Gift`.
    * If you call a subclass, you will only get proxies of that type. For example,
      ``Feature.get_proxies()`` will return a list containing a single
      :class:`Feature` object containing the Front Row Seat subdocument.


That's A Wrap
-------------

Take a closer look at the :mod:`sample/mongo_objects_sample.py` to see the
interplay between :class:`MongoUserDict` parent documents and the three
subdocument proxy types.

Observe some commong coding patterns. For example, since proxy objects can
only exist after the parent document is loaded, proxy loading methods like
:meth:`.loadBenefitById`, :meth:`.loadTicketTypeById` and
:meth:`.loadVenueById` are usually class methods of the parent document class
:class:`Event`.

Likewise, proxy creation method like :meth:`.getTicket`, :meth:`.getTickets`,
:meth:`.getTicketsByType`, :meth:`.getTicketType`, :meth:`.getTicketTypes` and
:meth:`.getVenue` are placed in the parent document class as well.

Refer to the rest of the documentation for information on other features like
:class:`PolymorphicMongoUserDict` polymorphic documents.
