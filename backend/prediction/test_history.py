import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from prediction.history import current_seasons, refresh


class HistoryTests(unittest.TestCase):
    def test_season_boundaries(self):
        self.assertEqual(current_seasons(datetime(2026, 6, 1, tzinfo=timezone.utc)), ["2425", "2526"])
        self.assertEqual(current_seasons(datetime(2026, 10, 31, tzinfo=timezone.utc)), ["2526", "2627"])

    def test_invalid_download_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "E0_2627.csv"
            original = b"Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n2026-10-25,Alpha,Beta,2,1,H\n"
            path.write_bytes(original)
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b"<html>provider error</html>"
            with patch("prediction.history.urlopen", return_value=response):
                with self.assertRaises(ValueError):
                    refresh(root, ["2627"])
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(path.with_suffix(".tmp").exists())
