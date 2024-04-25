Introduction To mongo_objects
=============================

Overview
--------

mongo_objects wraps pymongo functionality with new classes to simplify access to MongoDB
documents and subdocuments.

Documents are returned as user-defined UserDict subclasses, seamlessly linking user code
with MongoDB data.

Subdocuments are access through user-defined, dictionary-like subclasses that redirect
all access back to the original parent document.


Installation
------------

Install from PyPI. We recommend installing into the virtual environment
for your Python project.::

    pip install mongo_objects


Quickstart
-------------------

Check out the :doc:`quickstart` documentation for a brief overview of document
and subdocument features.

See the :doc:`sample` code for a working demonstration.


MongoDB Documents
-----------------

* :doc:`MongoUserDict`


Sub-Document Proxies
--------------------

* :doc:`MongoDictProxy`
* :doc:`MongoListProxy`
* :doc:`MongoSingleProxy`


Additional Information
----------------------
* :doc:`customization`


Credits
-------

Development sponsored by `Headwaters Entrepreneurs Pte Ltd <https://headwaters.com.sg>`_.

Originally developed by `Frontier Tech Team LLC <https://frontiertechteam.com>`_
for the `Wasted Minutes <https://wasted-minutes.com>`_ ™️ language study tool.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   MongoUserDict
   MongoDictProxy
   MongoListProxy
   MongoSingleProxy
   sample
   customization


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
