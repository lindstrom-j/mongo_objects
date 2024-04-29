Proxy Overview
==============

MongoDB allows documents to contain sub-dictionaries, whether single
subdictionaries, dictionaries of sub-dictionaries or lists of sub-dictionaries.
These sub-dictionaries are all considered forms of *subdocuments*.

:mod:`mongo_objects` provides proxy classes to that allow subdocuments to be
managed with their own custom classes while referencing the data within the parent
document. Proxying offers several advantages:

* Once the parent document is loaded, no additional database access is required
  to access the subdocuments
* No data is copied from parent to proxy, so the parent document remains
  the single source of truth
* Proxy subdocument classes organize the functions required for the subdocument
  separate from functions for the parent document itself

Note that *parent* here refers to the top-level MongoDB document that may contain
various levels of subdocuments. No object oriented inheritance between the
top-level document and subdocument classes is implied.

Proxy Class Variants
--------------------

:mod:`mongo_objects` supports three different types of proxies. See the specific
documentation for each class to learn more.

* :class:`MongoDictProxy` uses a dictionary to contain a group of related subdocuments
* :class:`MongoListProxy` uses a list to contain a group of related subdocuments
* :class:`MongoSingleProxy` references a single subdocument as its own class


Features
--------

**Dictionary-Like**: All proxy objects support standard dictionary access methods. See the class reference
below for further details.

**Polymorphism**: Subdocument proxy classes support polymorphic classes within the same container.

**Multi-level**: Proxy objects may be nested to as many levels as desired.

**Subdocument IDs**: A unique number exactly identifies each proxy object within the parent document.


Class Reference
----------------

.. currentmodule:: mongo_objects
.. autoclass:: MongoBaseProxy
    :special-members:
    :members: create_key, data, get, id, items, keys, setdefault, update, save, values


.. autoclass:: PolymorphicMongoBaseProxy
    :special-members:
    :members:

