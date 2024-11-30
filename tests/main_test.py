import unittest
from unittest.mock import patch, MagicMock, mock_open
from bs4 import BeautifulSoup
from io import StringIO
import pickle

from main import build_user_config_ir, is_valid_user_config, C1WebSitePollAndWriter, UserConfigIR, UserConfigIRForSingleWebSite, VisitedLinkCache


class TestUserConfigIR(unittest.TestCase):

    def test_add_entry_and_retrieval(self):
        user_config_ir = UserConfigIR()
        site_config = UserConfigIRForSingleWebSite()
        site_config.alias = "test_alias"
        user_config_ir.add_entry("test_alias", site_config)
        retrieved = user_config_ir.get_user_config_ir_for_single_web_site("test_alias")
        self.assertEqual(retrieved, site_config)

    def test_update_blocked_author_name_set(self):
        site_config = UserConfigIRForSingleWebSite()
        site_config.update_blocked_author_name_set("blocked_author")
        self.assertIn("blocked_author", site_config.blocked_author_name_set)


class TestC1WebSitePollAndWriter(unittest.TestCase):

    @patch("requests.get")
    def test_get_page_dump(self, mock_get):
        mock_get.return_value = MagicMock(text="<html></html>", status_code=200)
        poller = C1WebSitePollAndWriter()
        result = poller._get_page_dump()
        self.assertEqual(result, "<html></html>")

    def test_get_list_of_article_meta_tuples(self):
        poller = C1WebSitePollAndWriter()
        html_content = """
        <div class="list_author">
            <span class="memo">Memo text</span>
            <span title="author_name"></span>
            <div class="list_title"><a href="/link"></a></div>
        </div>
        """
        result = poller._get_list_of_article_meta_tuples(html_content)
        expected_result = [("https://www.clien.net/link", "author_name", "Memo text")]
        self.assertEqual(result, expected_result)

    @patch.object(VisitedLinkCache, 'is_hit', return_value=False)
    @patch.object(VisitedLinkCache, 'add_entry')
    def test_write_output_no_cache_hit(self, mock_add_entry, mock_is_hit):
        poller = C1WebSitePollAndWriter()
        poller.client_context = MagicMock()
        poller.client_context.driver = MagicMock()

        poller._write_output("test_link")
        poller.client_context.driver.get.assert_called_once_with("test_link")
        mock_add_entry.assert_called_once_with("test_link")

class TestConfigValidation(unittest.TestCase):

    def test_is_valid_user_config_valid(self):
        valid_config = {
            "web_site": [
                {
                    "alias": "test_site",
                    "user": {"id": "test_user", "pw": "test_pw"},
                    "blocked_author_memo_pattern": "test_pattern",
                    "polling_interval": {"median": 180, "upper_limit": 10, "lower_limit": -10},
                }
            ]
        }
        self.assertTrue(is_valid_user_config(valid_config))

    def test_is_valid_user_config_invalid(self):
        invalid_config = {
            "web_site": [
                {
                    "alias": "test_site",
                    "user": {"id": "test_user"},  # missing 'pw'
                    "blocked_author_memo_pattern": "test_pattern",
                }
            ]
        }
        self.assertFalse(is_valid_user_config(invalid_config))

    def test_build_user_config_ir(self):
        config_dict = {
            "web_site": [
                {
                    "alias": "test_site",
                    "user": {"id": "user_id", "pw": "user_pw"},
                    "blocked_author_name": ["blocked1"],
                    "blocked_author_memo_pattern": "pattern1",
                }
            ]
        }
        user_config_ir = build_user_config_ir(config_dict)
        site_config = user_config_ir.get_user_config_ir_for_single_web_site("test_site")
        self.assertEqual(site_config.user_id, "user_id")
        self.assertIn("blocked1", site_config.blocked_author_name_set)


if __name__ == "__main__":
    unittest.main()
