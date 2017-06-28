# -*- coding: utf-8 -*-
"""
clipster - python clipboard manager
"""

from setuptools import find_packages, setup

dependencies = []
setup_requires = ['setuptools_scm']

setup(
    name = "clipster",
    setup_requires=setup_requires,
    use_scm_version=True,
    url = "https://github.com/mrichar1/clipster",
    license='LICENSE.md',
    author = "Matthew Richardson",
    author_email = "",
    description='python clipboard manager',
    long_description=__doc__,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    data_files = [("share/licenses/clipster", ["LICENSE.md"]), ("share/doc/clipster", ["README.md"])],
    zip_safe=False,
    platforms='any',
    install_requires=dependencies,
    scripts = ['clipster'],
    classifiers=[
        # As from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        # 'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        # 'Development Status :: 4 - Beta',
        'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Environment :: Console',
        'Environment :: X11 Applications',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ]
)
