from openmock import behaviour
from tests import Testopenmock


class TestopenmockBehaviour(Testopenmock):
    def tearDown(self):
        behaviour.disable_all()
