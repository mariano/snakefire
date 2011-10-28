import unittest, sys, os, xmlrunner
sys.path.append('snakefire')
from snakefire_test import TestSnakefire

if __name__ == '__main__':
    testSuite = unittest.TestLoader().loadTestsFromTestCase(TestSnakefire)
    xmlrunner.XMLTestRunner(output='reports').run(testSuite)
    
