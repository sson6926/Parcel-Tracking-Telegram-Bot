"""Unit tests for order list pagination and non-blocking provider client reuse."""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.handlers.tracking_handler import PAGE_SIZE, TrackingHandler
from app.providers.ghn.client import GHNProvider
from app.providers.jtexpress.client import JTExpressProvider
from app.providers.shopeeexpress.client import ShopeeExpressProvider


class TestPaginationCalculations(unittest.TestCase):
    def test_total_pages(self):
        self.assertEqual(PAGE_SIZE, 5)

        def calc_pages(total):
            return max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

        self.assertEqual(calc_pages(0), 1)
        self.assertEqual(calc_pages(1), 1)
        self.assertEqual(calc_pages(5), 1)
        self.assertEqual(calc_pages(6), 2)
        self.assertEqual(calc_pages(10), 2)
        self.assertEqual(calc_pages(11), 3)

    def test_item_slices(self):
        items = list(range(1, 13))  # 12 items: 1..12

        # Page 1 -> items[0:5] = [1, 2, 3, 4, 5]
        self.assertEqual(items[0:5], [1, 2, 3, 4, 5])
        # Page 2 -> items[5:10] = [6, 7, 8, 9, 10]
        self.assertEqual(items[5:10], [6, 7, 8, 9, 10])
        # Page 3 -> items[10:15] = [11, 12]
        self.assertEqual(items[10:15], [11, 12])


class TestTrackingHandlerPagination(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_i18n = MagicMock()
        self.mock_i18n.t.side_effect = lambda key, lang, **kw: key
        self.mock_service = MagicMock()
        self.handler = TrackingHandler(self.mock_i18n, self.mock_service)

    async def test_pagination_buttons_multi_page(self):
        # Create 12 mock trackings
        mock_trackings = []
        for i in range(1, 13):
            t = MagicMock()
            t.id = i
            t.tracking_code = f"TRACK{i:03d}"
            t.last_status = "IN_TRANSIT"
            t.is_active = True
            mock_trackings.append(t)

        self.mock_service.list_trackings.return_value = mock_trackings

        mock_update = MagicMock()
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {"language": "vi"}

        # Show page 1 of 3
        with patch.object(self.handler, "_send_or_edit", new_callable=AsyncMock) as mock_send_edit:
            await self.handler._show_order_list(123, mock_update, mock_context, "vi", page=1)

            self.assertTrue(mock_send_edit.called)
            keyboard = mock_send_edit.call_args[0][4]
            # Buttons: 5 order rows + 1 nav row + 1 filter row + 1 back row = 8 rows
            self.assertEqual(len(keyboard.inline_keyboard), 8)

            # Check nav row (second to last)
            nav_row = keyboard.inline_keyboard[5]
            button_texts = [b.text for b in nav_row]
            button_data = [b.callback_data for b in nav_row]

            # Page 1 has no previous button: [📄 1/3, ▶️]
            self.assertIn("📄 1/3", button_texts)
            self.assertIn("▶️", button_texts)
            self.assertIn("page:all:2", button_data)

        # Show page 2 of 3
        with patch.object(self.handler, "_send_or_edit", new_callable=AsyncMock) as mock_send_edit:
            await self.handler._show_order_list(123, mock_update, mock_context, "vi", page=2)

            keyboard = mock_send_edit.call_args[0][4]
            nav_row = keyboard.inline_keyboard[5]
            button_texts = [b.text for b in nav_row]
            button_data = [b.callback_data for b in nav_row]

            # Page 2 has both previous and next: [◀️, 📄 2/3, ▶️]
            self.assertIn("◀️", button_texts)
            self.assertIn("📄 2/3", button_texts)
            self.assertIn("▶️", button_texts)
            self.assertIn("page:all:1", button_data)
            self.assertIn("page:all:3", button_data)

    async def test_pagination_buttons_single_page(self):
        # 3 mock trackings (<= 5)
        mock_trackings = []
        for i in range(1, 4):
            t = MagicMock()
            t.id = i
            t.tracking_code = f"TRACK{i:03d}"
            t.last_status = "IN_TRANSIT"
            t.is_active = True
            mock_trackings.append(t)

        self.mock_service.list_trackings.return_value = mock_trackings

        mock_update = MagicMock()
        mock_update.callback_query = MagicMock()
        mock_update.callback_query.edit_message_text = AsyncMock()
        mock_context = MagicMock()

        with patch.object(self.handler, "_send_or_edit", new_callable=AsyncMock) as mock_send_edit:
            await self.handler._show_order_list(123, mock_update, mock_context, "vi", page=1)

            keyboard = mock_send_edit.call_args[0][4]
            # Rows: 3 order rows + 1 filter row + 1 back row = 5 rows (NO nav row!)
            self.assertEqual(len(keyboard.inline_keyboard), 5)

    async def test_page_callback_routing(self):
        mock_update = MagicMock()
        mock_query = MagicMock()
        mock_query.data = "page:active:2"
        mock_query.answer = AsyncMock()
        mock_update.callback_query = mock_query
        mock_update.effective_chat.id = 123
        mock_context = MagicMock()
        mock_context.user_data = {"language": "vi"}

        with patch.object(self.handler, "_show_order_list", new_callable=AsyncMock) as mock_show:
            await self.handler.page_callback(mock_update, mock_context)
            mock_show.assert_called_once_with(
                123, mock_update, mock_context, "vi", status_filter="active", page=2
            )


class TestProviderClientPooling(unittest.TestCase):
    def test_ghn_client_reuse(self):
        provider = GHNProvider(timeout_seconds=5.0)
        c1 = provider._get_client()
        c2 = provider._get_client()
        self.assertIs(c1, c2)
        provider.close()
        self.assertTrue(c1.is_closed)
        # After close, _get_client creates fresh active client
        c3 = provider._get_client()
        self.assertIsNot(c1, c3)
        self.assertFalse(c3.is_closed)
        provider.close()

    def test_shopee_client_reuse(self):
        provider = ShopeeExpressProvider(timeout_seconds=5.0)
        c1 = provider._get_client()
        c2 = provider._get_client()
        self.assertIs(c1, c2)
        provider.close()
        self.assertTrue(c1.is_closed)
        provider.close()

    def test_jtexpress_client_reuse(self):
        provider = JTExpressProvider(timeout_seconds=5.0)
        c1 = provider._get_client()
        c2 = provider._get_client()
        self.assertIs(c1, c2)
        provider.close()
        self.assertTrue(c1.is_closed)
        provider.close()


if __name__ == "__main__":
    unittest.main()
