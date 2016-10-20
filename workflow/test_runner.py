# -*- coding: UTF-8 -*-
"""

A custom test runner that includes reporting of unit test coverage. Based upon
code found here:
"""
import os
import sys
import shutil
import unittest

import coverage

from django.test.SimpleTestCase import run_tests as django_test_runner
from django.conf import settings

# Look for coverage.py in __file__/lib as well as sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))


def test_runner_with_coverage(test_labels, verbosity=1, interactive=True, extra_tests=None):
    """
    Custom test runner.  Follows the django.test.simple.run_tests() interface.
    """
    # Start code coverage before anything else if necessary
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage.use_cache(0)  # Do not cache any of the coverage.py stuff
        coverage.start()

    test_results = django_test_runner(test_labels, verbosity, interactive, extra_tests)

    # Stop code coverage after tests have completed
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage.stop()

    # Print code metrics header
    print ''
    print '----------------------------------------------------------------------'
    print ' Unit Test Code Coverage Results'
    print '----------------------------------------------------------------------'

    # Report code coverage metrics
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage_modules = []
        for module in settings.COVERAGE_MODULES:
            coverage_modules.append(__import__(module, globals(), locals(), ['']))
        coverage.report(coverage_modules, show_missing=1)
        # Print code metrics footer
        print '----------------------------------------------------------------------'

    return test_results
