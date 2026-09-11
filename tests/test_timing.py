"""Unit tests for processing time tracking and message formatting."""
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.utils.chat_action import with_typing_action
from app.utils.timing import (
    TimedBot,
    append_processing_time,
    current_request_chat_id,
    current_request_lang,
    current_request_start_time,
    format_timing_footer,
    reset_request_context,
    set_request_context,
    strip_timing_footer,
    update_request_lang,
)


class TestTimingFormatting(unittest.TestCase):
    def test_format_timing_footer_html(self):
        footer_vi = format_timing_footer(0.123, lang="vi", parse_mode="HTML")
        self.assertEqual(footer_vi, "\n\n<i>⏱️ Thời gian xử lý: 0.12s</i>")

        footer_en = format_timing_footer(1.5, lang="en", parse_mode="HTML")
        self.assertEqual(footer_en, "\n\n<i>⏱️ Processing time: 1.50s</i>")

        footer_ja = format_timing_footer(0.05, lang="ja", parse_mode="HTML")
        self.assertEqual(footer_ja, "\n\n<i>⏱️ 処理時間: 0.05s</i>")

    def test_format_timing_footer_plain(self):
        footer = format_timing_footer(0.45, lang="vi", parse_mode=None)
        self.assertEqual(footer, "\n\n⏱️ Thời gian xử lý: 0.45s")

    def test_format_timing_footer_min_elapsed(self):
        footer = format_timing_footer(0.0001, lang="vi", parse_mode="HTML")
        self.assertEqual(footer, "\n\n<i>⏱️ Thời gian xử lý: 0.01s</i>")

    def test_strip_timing_footer(self):
        samples = [
            ("Hello world\n\n<i>⏱️ Thời gian xử lý: 0.12s</i>", "Hello world"),
            ("Hello world\n\n⏱️ Thời gian xử lý: 0.12s", "Hello world"),
            ("Hello world\n\n<i>⏱️ 0.12s</i>", "Hello world"),
            ("Hello world\n\n⏱️ Processing time: 0.45s", "Hello world"),
            ("Hello world\n\n<i>⏱️ 処理時間: 0.05s</i>", "Hello world"),
            ("Hello world without footer", "Hello world without footer"),
        ]
        for raw, expected in samples:
            with self.subTest(raw=raw):
                self.assertEqual(strip_timing_footer(raw), expected)


class TestAppendProcessingTime(unittest.TestCase):
    def test_no_context_returns_original_text(self):
        # When called outside a user request (e.g. scheduler)
        self.assertIsNone(current_request_start_time.get())
        text = "Periodic notification"
        result = append_processing_time(text, chat_id=123, parse_mode="HTML")
        self.assertEqual(result, text)

    def test_loading_indicator_skipped(self):
        tokens = set_request_context(123, lang="vi")
        try:
            text = "<b>⏳ Đang kiểm tra đơn hàng...</b>"
            result = append_processing_time(text, chat_id=123, parse_mode="HTML")
            self.assertEqual(result, text)
        finally:
            reset_request_context(tokens)

    def test_different_chat_id_skipped(self):
        tokens = set_request_context(100, lang="vi")
        try:
            text = "Broadcast message to other users"
            # Target chat is 200, current request is for chat 100
            result = append_processing_time(text, chat_id=200, parse_mode="HTML")
            self.assertEqual(result, text)
        finally:
            reset_request_context(tokens)

    def test_active_context_appends_timing(self):
        tokens = set_request_context(123, lang="vi")
        try:
            text = "<b>Đơn hàng đã được tạo thành công</b>"
            result = append_processing_time(text, chat_id=123, parse_mode="HTML")
            self.assertTrue(result.startswith(text))
            self.assertIn("<i>⏱️ Thời gian xử lý:", result)
        finally:
            reset_request_context(tokens)

    def test_re_edit_replaces_old_footer(self):
        tokens = set_request_context(123, lang="vi")
        try:
            original = "<b>Chi tiết đơn hàng</b>\n\n<i>⏱️ Thời gian xử lý: 0.05s</i>"
            result = append_processing_time(original, chat_id=123, parse_mode="HTML")
            # Should have only ONE timing footer, not stacked
            self.assertEqual(result.count("⏱️"), 1)
            self.assertTrue(result.startswith("<b>Chi tiết đơn hàng</b>\n\n<i>⏱️ Thời gian xử lý:"))
        finally:
            reset_request_context(tokens)

    def test_max_telegram_length(self):
        tokens = set_request_context(123, lang="vi")
        try:
            long_text = "A" * 4095
            result = append_processing_time(long_text, chat_id=123, parse_mode="HTML")
            self.assertLessEqual(len(result), 4096)
            self.assertTrue(result.endswith("</i>"))
        finally:
            reset_request_context(tokens)


class TestWithTypingAction(unittest.IsolatedAsyncioTestCase):
    async def test_context_lifecycle(self):
        handler_ran = False
        captured_time = None
        captured_chat = None
        captured_lang = None

        async def dummy_handler(update, context):
            nonlocal handler_ran, captured_time, captured_chat, captured_lang
            handler_ran = True
            captured_time = current_request_start_time.get()
            captured_chat = current_request_chat_id.get()
            captured_lang = current_request_lang.get()
            return "OK"

        wrapped = with_typing_action(dummy_handler)

        mock_update = MagicMock()
        mock_update.effective_chat.id = 456
        mock_context = MagicMock()
        mock_context.user_data = {"language": "en"}
        mock_context.bot.send_chat_action = AsyncMock()

        res = await wrapped(mock_update, mock_context)
        self.assertEqual(res, "OK")
        self.assertTrue(handler_ran)
        self.assertIsNotNone(captured_time)
        self.assertEqual(captured_chat, 456)
        self.assertEqual(captured_lang, "en")

        # After handler finishes, context should be reset
        self.assertIsNone(current_request_start_time.get())
        self.assertIsNone(current_request_chat_id.get())


class TestTimedBot(unittest.IsolatedAsyncioTestCase):
    async def test_send_message_intercept(self):
        bot = TimedBot("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        captured_args = None
        captured_kwargs = None

        async def mock_super_send(*args, **kwargs):
            nonlocal captured_args, captured_kwargs
            captured_args = args
            captured_kwargs = kwargs
            return MagicMock()

        # Monkey-patch super call on bot for isolated testing
        from telegram import Bot
        orig_send = Bot.send_message
        Bot.send_message = mock_super_send

        try:
            tokens = set_request_context(123, lang="vi")
            try:
                # Call send_message with kwargs
                await bot.send_message(chat_id=123, text="Test message", parse_mode="HTML")
                self.assertIn("text", captured_kwargs)
                self.assertIn("⏱️ Thời gian xử lý:", captured_kwargs["text"])

                # Call send_message with positional args
                await bot.send_message(123, "Positional message", "HTML")
                self.assertIn("text", captured_kwargs)
                self.assertIn("⏱️ Thời gian xử lý:", captured_kwargs["text"])
            finally:
                reset_request_context(tokens)
        finally:
            Bot.send_message = orig_send

    async def test_edit_message_text_intercept(self):
        bot = TimedBot("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        captured_args = None
        captured_kwargs = None

        async def mock_super_edit(*args, **kwargs):
            nonlocal captured_args, captured_kwargs
            captured_args = args
            captured_kwargs = kwargs
            return MagicMock()

        from telegram import Bot
        orig_edit = Bot.edit_message_text
        Bot.edit_message_text = mock_super_edit

        try:
            tokens = set_request_context(123, lang="ja")
            try:
                # Call edit_message_text with kwargs
                await bot.edit_message_text(text="Edit message", chat_id=123, message_id=1, parse_mode="HTML")
                self.assertIn("text", captured_kwargs)
                self.assertIn("⏱️ 処理時間:", captured_kwargs["text"])

                # Call edit_message_text with positional args
                await bot.edit_message_text("Positional edit", 123, 1, None, None, "HTML")
                self.assertIn("text", captured_kwargs)
                self.assertIn("⏱️ 処理時間:", captured_kwargs["text"])
            finally:
                reset_request_context(tokens)
        finally:
            Bot.edit_message_text = orig_edit


if __name__ == "__main__":
    unittest.main()

