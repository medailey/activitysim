
Getting Started
===============

This page describes how to get started with ActivitySim.

.. note::
   ActivitySim is under development

.. index:: installation

Installation
------------

The following installation instructions are for Windows or Mac users.  ActivitySim is built
to run on one machine with sufficient available RAM to fit all required data and calculations
in memory.

Anaconda
~~~~~~~~

ActivitySim is a 64bit Python 2.7 library that uses a number of packages from the
scientific Python ecosystem, most notably `pandas <http://pandas.pydata.org>`__ 
and `numpy <http://numpy.org>`__. ActivitySim does not currently support Python 3.
   
The recommended way to get your own scientific Python installation is to
install Anaconda_ 2 64bit, which contains many of the libraries upon which
ActivitySim depends + some handy Python installation management tools.  

Anaconda includes the ``conda`` command line tool, which does a number of useful 
things, including creating `environments <http://conda.pydata.org/docs/using/envs.html>`__ 
(i.e. stand-alone Python installations/instances/sandboxes) that are the recommended 
way to work with multiple versions of Python on one machine.  Using conda 
environments keeps multiple Python setups from conflicting with one another.

After installing Anaconda, create an ActivitySim test environment 
with the following commands:

::
    
    #Windows
    conda create -n asimtest python=2.7
    activate asimtest

    #Mac
    conda create -n asimtest python=2.7
    source activate asimtest

If you access the internet from behind a firewall, then you will need to configure your proxy 
server. To do so, create a ``.condarc`` file in your Anaconda installation folder, such as:

::
    
    proxy_servers:
      http: http://myproxy.org:8080
      https: https://myproxy.org:8080
    ssl_verify: false

This will create a new conda environment named ``asimtest`` and set it as the 
active conda environment.  You need to activate the environment each time you
start a new command session.  You can remove an environment with 
``conda remove -n asimtest --all`` and check the current active environment with
``conda info -e``.

Dependencies
~~~~~~~~~~~~

ActivitySim depends on the following libraries, some of which* are pre-installed
with Anaconda:

* `numpy <http://numpy.org>`__ >= 1.13.0 \*
* `pandas <http://pandas.pydata.org>`__ >= 0.20.3 \*
* `pyyaml <http://pyyaml.org/wiki/PyYAML>`__ >= 3.0 \*
* `tables <http://www.pytables.org/moin>`__ >= 3.3.0 \*
* `toolz <http://toolz.readthedocs.org/en/latest/>`__ or
  `cytoolz <https://github.com/pytoolz/cytoolz>`__ >= 0.7 \*
* `psutil <https://pypi.python.org/pypi/psutil>`__ >= 4.1
* `zbox <https://pypi.python.org/pypi/zbox>`__ >= 1.2
* `orca <https://udst.github.io/orca>`__ >= 1.1
* `openmatrix <https://pypi.python.org/pypi/OpenMatrix>`__ >= 0.2.4

To install the dependencies with conda, first make sure to activate the correct
conda environment and then install each package using pip_.  Pip will 
attempt to install any dependencies that are not already installed.  

::
    
    #required packages for running ActivitySim
    pip install cytoolz numpy pandas tables pyyaml psutil
    pip install orca openmatrix zbox
    
    #optional required packages for testing and building documentation
    pip install pytest pytest-cov coveralls pycodestyle
    pip install sphinx numpydoc sphinx_rtd_theme

If numexpr (which numpy requires) fails to install, you may need 
the `Microsoft Visual C++ Compiler for Python <http://aka.ms/vcpython27>`__. 

If you access the internet from behind a firewall, then you will need to configure 
your proxy server when downloading packages.  For example:

::
    
    pip install --trusted-host pypi.python.org --proxy=myproxy.org:8080  cytoolz

ActivitySim
~~~~~~~~~~~

The current ``release`` version of ActivitySim can be installed 
from `PyPI <https://pypi.python.org/pypi/activitysim>`__  as well using pip_.  
The development version can be installed directly from the source.

Release
^^^^^^^

::
    
    #new install
    pip install activitysim

    #update to a new release
    pip install -U activitysim

Development
^^^^^^^^^^^

The development version of ActivitySim can be installed as follows:

* Clone or fork the source from the `GitHub repository <https://github.com/udst/activitysim>`__
* Activate the correct conda environment if needed
* Navigate to your local activitysim git directory
* Run the command ``python setup.py develop``

The ``develop`` command is required in order to make changes to the 
source and see the results without reinstalling.  You may need to first uninstall the
the pip installed version before installing the development version from source.  This is 
done with ``pip uninstall activitysim``.

.. _Anaconda: http://docs.continuum.io/anaconda/index.html
.. _conda: http://conda.pydata.org/
.. _pip: https://pip.pypa.io/en/stable/

.. _expressions_in_detail :

Hardware
--------

The computing hardware required to run an ActivitySim-based model generally depends on:

* the number of households to be simulated
* the number and size of network skims (i.e. the number of model zones (for each zone system if applicable))
* the desired runtimes

ActivitySim requires a substantial amount of RAM since it stores data in-memory in order to minimize runtimes.
For example, the example model is tested on a Windows server with 256GB of RAM and 48 threads.  ActivitySim
is NOT currently multi-threaded/processed, but this improvement is in the development roadmap.

Expressions
-----------

Much of the power of ActivitySim comes from being able to specify Python, pandas, and 
numpy expressions for calculations. Refer to the pandas help for a general 
introduction to expressions.  ActivitySim provides two ways to evaluate expressions:

* Simple table expressions are evaluated using ``DataFrame.eval()``.  `pandas' eval <http://pandas.pydata.org/pandas-docs/stable/generated/pandas.eval.html>`__ operates on the current table.
* Python expressions, denoted by beginning with ``@``, are evaluated with `Python's eval() <https://docs.python.org/2/library/functions.html#eval>`__.

Simple table expressions can only refer to columns in the current DataFrame.  Python expressions can refer to any Python objects 
currently in memory.

Conventions
~~~~~~~~~~~

There are a few conventions for writing expressions in ActivitySim:

* each expression is applied to all rows in the table being operated on
* expressions must be vectorized expressions and can use most numpy and pandas expressions
* global constants are specified in the settings file
* comments are specified with ``#``
* you can refer to the current table being operated on as ``df``
* often an object called ``skims``, ``skims_od``, or similar is available and is used to lookup the relevant skim information.  See :ref:`skims_in_detail` for more information.
* when editing the CSV files in Excel, use single quote ' or space at the start of a cell to get Excel to accept the expression

Example Expressions File
~~~~~~~~~~~~~~~~~~~~~~~~

An expressions file has the following basic form:

+---------------------------------+-------------------------------+-----------+----------+
| Description                     |  Expression                   |     cars0 |    cars1 |
+=================================+===============================+===========+==========+
| 2 Adults (age 16+)              |  drivers==2                   |         0 |   3.0773 |
+---------------------------------+-------------------------------+-----------+----------+
| Persons age 35-34               |  num_young_adults             |         0 |  -0.4849 |
+---------------------------------+-------------------------------+-----------+----------+
| Number of workers, capped at 3  |  @df.workers.clip(upper=3)    |         0 |   0.2936 |
+---------------------------------+-------------------------------+-----------+----------+
| Distance, from 0 to 1 miles     |  @skims['DIST'].clip(1)       |   -3.2451 |  -0.9523 |
+---------------------------------+-------------------------------+-----------+----------+

* Rows are vectorized expressions that will be calculated for every record in the current table being operated on
* The Description column describes the expression
* The Expression column contains a valid vectorized Python/pandas/numpy expression.  In the example above, ``drivers`` is a column in the current table.  Use ``@`` to refer to data outside the current table
* There is a column for each alternative and its relevant coefficient

See :ref:`expressions` for more information.
