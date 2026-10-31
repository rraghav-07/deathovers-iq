"""Regression: the database connection must close before filesystem changes."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('loader', ROOT/'etl/load_data.py')
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)

class TrackedConnection(sqlite3.Connection):
    closed = False

    def close(self):
        super().close()
        self.closed = True

class LoaderLifecycle(unittest.TestCase):
    def test_close_before_replace_and_failure_cleanup(self):
        real_connect = sqlite3.connect
        real_replace = loader.os.replace
        real_unlink = loader.os.unlink
        connections = []

        def connect(*args, **kwargs):
            con = real_connect(*args, factory=TrackedConnection, **kwargs)
            connections.append(con)
            return con

        def replace(*args):
            self.assertTrue(all(c.closed for c in connections))
            return real_replace(*args)

        def unlink(*args):
            self.assertTrue(all(c.closed for c in connections))
            return real_unlink(*args)

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'test.sqlite'
            with patch.object(loader.sqlite3,'connect',side_effect=connect), \
                 patch.object(loader.os,'replace',side_effect=replace), \
                 patch.object(loader.os,'unlink',side_effect=unlink), \
                 contextlib.redirect_stdout(io.StringIO()):
                for _ in range(2):
                    loader.build(ROOT/'data/raw', target)
                original = target.read_bytes()
                with patch.object(loader,'EXTRAS',set()), self.assertRaises(ValueError):
                    loader.build(ROOT/'data/raw', target)
                self.assertEqual(target.read_bytes(),original)
                self.assertEqual(list(Path(tmp).glob('tmp*.sqlite')),[])

if __name__=='__main__':
    unittest.main()
