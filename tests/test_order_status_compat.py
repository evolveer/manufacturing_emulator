import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "erp"))

from services import OrderService


class OrderStatusCompatTest(unittest.TestCase):
    def test_normalize_order_status_maps_legacy_values(self):
        self.assertEqual(OrderService.normalize_order_status("pending"), "draft")
        self.assertEqual(OrderService.normalize_order_status("in_progress"), "in_production")

    def test_normalize_order_status_preserves_canonical_values(self):
        self.assertEqual(OrderService.normalize_order_status("draft"), "draft")
        self.assertEqual(OrderService.normalize_order_status("completed"), "completed")
        self.assertEqual(OrderService.normalize_order_status(None), "draft")


if __name__ == "__main__":
    unittest.main()
