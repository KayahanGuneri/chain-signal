import unittest

from chainsignal_pipeline import __version__


class BootstrapTest(unittest.TestCase):
    def test_version_is_defined(self) -> None:
        self.assertEqual("0.1.0", __version__)


if __name__ == "__main__":
    unittest.main()