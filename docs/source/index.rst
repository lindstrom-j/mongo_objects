Introduction To mongo_objects
=============================

Overview
--------

mongo_objects wraps pymongo with new classes to simplify access to MongoDB
documents and subdocuments.

Documents are returned as user-defined UserDict subclasses, seamlessly linking user code
with MongoDB data.

Subdocuments are accessed through user-defined, dictionary-like subclasses that proxy
data from the original parent document.


Installation
------------

Install from `PyPI <https://pypi.org/project/mongo-objects>`_. We recommend installing into the virtual environment
for your Python project.::

    pip install mongo_objects

The source code is also available `GitHub <https://github.com/lindstrom-j/mongo_objects>`_.

Getting Started
---------------

Check out the :doc:`quickstart` documentation for a brief overview of document
and subdocument features.

See the :doc:`sample` code for a working demonstration.

.. toctree::
   :maxdepth: 2

   quickstart
   sample


MongoDB Documents
-----------------

Return your MongoDB documents as customized UserDict subclasses.

.. toctree::
   :maxdepth: 2

   MongoUserDict


Sub-Document Proxies
--------------------

Manage subdocuments as lightweight dictionary-like proxies back to
the parent document object.

.. toctree::
   :maxdepth: 2

   proxy_overview
   MongoDictProxy
   MongoListProxy
   MongoSingleProxy


Credits
-------

Development sponsored by `Headwaters Entrepreneurs Pte Ltd <https://headwaters.com.sg>`_.

Originally developed by `Frontier Tech Team LLC <https://frontiertechteam.com>`_
for the `Wasted Minutes <https://wasted-minutes.com>`_ ™️ language study tool.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
