import os

from setuptools import setup

PACKAGE = os.path.basename(os.path.dirname(os.path.abspath(__file__))).replace('-', '_')
setup(
    name=PACKAGE,
    version="0.0.3",
    packages=[PACKAGE],
    test_suite='tests',
    ## Sample entry point
    entry_points = {
        'console_scripts': ['timesyncservice=timesync.timesyncservice:main',
                            'loc_timesyncservice=timesync.timesyncservice:main2']
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development',
        'Topic :: Utilities',
    ],
)
