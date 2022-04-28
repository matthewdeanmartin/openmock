# -*- coding: utf-8 -*-

from tests import Testopenmock


class TestPing(Testopenmock):

    def test_should_return_true_when_ping(self):
        self.assertTrue(self.es.ping())
