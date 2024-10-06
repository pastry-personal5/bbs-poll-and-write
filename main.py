"""
This program polls a predefined pattern from a bulletin board system.
If the pattern is found, it writes a predefined output to the bulletin board system.
TODO (@pastry-personal5): Avoid using Selenium to allow the program to run in a text-only environment.
"""

import os
import pickle
import random
import time

from bs4 import BeautifulSoup
from loguru import logger
import requests
import selenium
from selenium import common as SC
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import yaml
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class UserConfigIRForSingleWebSite:

    def __init__(self):
        self.alias = None
        self.user_id = None
        self.user_pw = None
        self.blocked_author_name_set = set()
        self.blocked_author_memo_pattern = None

    def update_blocked_author_name_set(self, author_name: str):
        self.blocked_author_name_set.update([author_name])


class UserConfigIR:

    def __init__(self):
        self.user_config_ir_for_single_web_site_dict = {}

    def get_user_config_ir_for_single_web_site(self, alias: str):
        return self.user_config_ir_for_single_web_site_dict[alias]

    def add_entry(self, alias: str, user_config_ir_for_single_web_site: UserConfigIRForSingleWebSite):
        self.user_config_ir_for_single_web_site_dict[alias] = user_config_ir_for_single_web_site


class VisitedLinkCache:

    const_pickle_filepath = './visited_link_cache_entries.pickle'

    def __init__(self):
        self.cache = set()
        self._load_permanent_entries()

    def add_entry(self, link: str):
        self.cache.update([link])
        self._do_permanent_save()

    def is_hit(self, link: str):
        return link in self.cache

    def _do_permanent_save(self):
        try:
            f = open(self.const_pickle_filepath, 'wb')
            pickle.dump(self.cache, f)
            f.close()
        except IOError as e:
            logger.error(e)

    def _load_permanent_entries(self):
        if not os.path.isfile(self.const_pickle_filepath):
            # Initially
            return

        # Load using python pickle.
        try:
            f = open(self.const_pickle_filepath, 'rb')
            self.cache = pickle.load(f)
            f.close()
        except IOError as e:
            logger.error(e)


class LinkVisitorClientContext:

    def __init__(self):
        self.driver = None  # It's a Selenium driver.

    def clean_up(self):
        if self.driver:
            self.driver.quit()


class C1WebSitePollAndWriter:

    def __init__(self):
        self.visited_link_cache = VisitedLinkCache()
        self.client_context = None

    def _get_page_dump(self):
        const_target_base_url = 'https://www.clien.net/service/board/park'

        # Send a request to the `const_target_base_url`
        try:
            logger.info(f'Try to get {const_target_base_url} ...')
            response = requests.get(const_target_base_url)
            return response.text
        except requests.exceptions.ConnectionError as e:
            logger.error(e)
            return None

    def _get_list_of_article_meta_tuples(self, page_dump: str) -> tuple[str, str, str]:
        # 1. Find text that represent an author name.
        #         i.e. Find all <span> elements with CSS class 'list_author'.
        # 2. Find a link or a URL to the article, also.
        # 3. Add (`author_name`, `article_link`) tuples to `list_of_author_name_and_article_link_tuple`.
        list_of_article_meta_tuples = []
        soup = BeautifulSoup(page_dump, 'html.parser')
        list_of_article_author_elements = soup.find_all('div', class_='list_author')
        for article_author_element in list_of_article_author_elements:
            # Find the first <span> element with a `title` attribute.
            # Please note that the title attribute specifies extra information about an element in HTML.
            author_memo = None  # Default
            memo_element = article_author_element.find('span', class_='memo')
            if memo_element:
                logger.info(f'Found {article_author_element}')
                author_memo = memo_element.text
            else:
                logger.info(f'Not found {article_author_element}')
            title_element = article_author_element.find('span', title=True)
            if title_element:
                # Let's get an author name from attribute `title` of that element.
                author_name = title_element['title']

                # Let's find a link to an article.
                article_element = article_author_element.parent

                if article_element:
                    subject_element = article_element.find('div', class_='list_title')
                    if subject_element:
                        a_tag = subject_element.find('a', href=True)
                        if a_tag:
                            const_service_base_url = 'https://www.clien.net'
                            article_link = const_service_base_url + a_tag['href']
                            # Finally, we got (`author_name`, `article_link`) tuple.
                            meta_tuple = (article_link, author_name, author_memo)
                            list_of_article_meta_tuples.append(meta_tuple)
        return list_of_article_meta_tuples

    def _write_output(self, article_link: str):
        if self.visited_link_cache.is_hit(article_link):
            logger.info(f'Cache hit. {article_link}')
            return

        # Write
        driver = self.client_context.driver
        assert driver is not None
        logger.info(f'Opening {article_link} ...')
        driver.get(article_link)
        const_time_to_wait = 16
        WebDriverWait(driver, const_time_to_wait).until(
            EC.presence_of_element_located((By.ID, 'editCommentTextarea'))
        )
        element_for_opening_comment_textarea = driver.find_element(By.CLASS_NAME, 'comment-open')
        element_for_opening_comment_textarea.click()
        const_time_to_sleep_in_sec = 12
        logger.info(f'Sleeping for {const_time_to_sleep_in_sec} second(s)...')
        time.sleep(const_time_to_sleep_in_sec)
        element_for_comment = driver.find_element(By.ID, 'editCommentTextarea')
        element_for_submission = driver.find_element(By.ID, 'rewrite_height')
        const_comment = '   '
        const_time_to_sleep_between_input_in_sec = 1
        logger.info(f'Sleeping for {const_time_to_sleep_between_input_in_sec} second(s)...')
        time.sleep(const_time_to_sleep_between_input_in_sec)
        element_for_comment.send_keys(const_comment)
        logger.info(f'Sleeping for {const_time_to_sleep_between_input_in_sec} second(s)...')
        time.sleep(const_time_to_sleep_between_input_in_sec)
        element_for_submission.click()

        # Finally.
        self.visited_link_cache.add_entry(article_link)

    def _do_oneshot_poll_and_write_bbs(self, user_config_ir_for_single_web_site: UserConfigIRForSingleWebSite) -> None:
        page_dump = self._get_page_dump()
        if not page_dump:
            return
        list_of_article_meta_tuples = self._get_list_of_article_meta_tuples(page_dump)
        # Filter and write
        for t in list_of_article_meta_tuples:
            article_link = t[0]
            author_name = t[1]
            author_memo = t[2]
            logger.info(f'Matching (({author_name}), ({author_memo}), ({article_link}))')
            if True:
                if author_name in user_config_ir_for_single_web_site.blocked_author_name_set:
                    logger.info(f'Found ({author_name}, {article_link})')
                    self._write_output(article_link)
            # If False. Because it's deprecated
            if False:
                if author_memo and author_memo.find(user_config_ir_for_single_web_site.blocked_author_memo_pattern) != -1:
                    logger.info(f'Found (({author_name}), ({author_memo}), ({article_link}))')
                    self._write_output(article_link)

    def _get_time_to_sleep_in_sec(self) -> int:
        const_base_time_to_sleep_in_sec = 30
        return const_base_time_to_sleep_in_sec + random.randrange(-10, 10)

    def _sleep_for_a_while(self) -> None:
        time_to_sleep_in_sec = self._get_time_to_sleep_in_sec()
        logger.info(f'Sleeping for {time_to_sleep_in_sec} second(s) ...')
        time.sleep(time_to_sleep_in_sec)

    def _create_link_visitor_client_context_with_selenium(self, user_id, user_pw):
        driver = webdriver.Chrome()
        driver.implicitly_wait(0.5)

        self.client_context = LinkVisitorClientContext()
        self.client_context.driver = driver

        self._visit_login_page(driver, user_id, user_pw)

    def _visit_login_page(self, driver, user_id, user_pw):
        driver.get('https://www.clien.net/service/')
        const_time_to_wait = 20
        WebDriverWait(driver, const_time_to_wait).until(
            EC.presence_of_element_located((By.ID, 'loginForm'))
        )

        element_for_id = driver.find_element(By.NAME, 'userId')
        element_for_password = driver.find_element(By.NAME, 'userPassword')
        element_for_submission = driver.find_element(By.NAME, '로그인하기')

        element_for_id.send_keys(user_id)
        element_for_password.send_keys(user_pw)
        element_for_submission.click()

        const_time_to_wait_for_login_modal_in_sec = 4
        logger.info(f'Sleeping for {const_time_to_wait_for_login_modal_in_sec} second(s)...')
        time.sleep(const_time_to_wait_for_login_modal_in_sec)

        try:
            element_not_to_register_device = driver.find_element(by=By.CLASS_NAME, value='modal_button_confirm')
            if element_not_to_register_device:
                element_not_to_register_device.click()
            const_time_to_wait_for_closing_in_sec = 4
            logger.info(f'Sleeping for {const_time_to_wait_for_closing_in_sec} second(s)...')
            time.sleep(const_time_to_wait_for_closing_in_sec)
        except SC.exceptions.NoSuchElementException:
            pass

    def _prepare(self, user_config_ir_for_single_web_site: UserConfigIRForSingleWebSite) -> None:
        user_id = user_config_ir_for_single_web_site.user_id
        user_pw = user_config_ir_for_single_web_site.user_pw
        self._create_link_visitor_client_context_with_selenium(user_id, user_pw)

    def poll_and_write_bbs(self, user_config_ir_for_single_web_site: UserConfigIRForSingleWebSite) -> None:
        self._prepare(user_config_ir_for_single_web_site)
        while True:
            self._do_oneshot_poll_and_write_bbs(user_config_ir_for_single_web_site)
            self._sleep_for_a_while()


def is_valid_user_config(user_config: dict) -> bool:
    if 'web_site' not in user_config:
        return False
    web_site = user_config['web_site']
    if len(web_site) <= 0:
        return False
    for w in web_site:
        if 'alias' not in w:
            return False
        if 'user' not in w:
            return False
        user = w['user']
        if 'id' not in user:
            return False
        if 'pw' not in user:
            return False
        if 'blocked_author_memo_pattern' not in w:
            return False
        blocked_author_memo_pattern = w['blocked_author_memo_pattern']
        if len(blocked_author_memo_pattern) <= 0:
            return False
    return True

def build_user_config_ir(user_config: dict) -> UserConfigIR:
    # Build an object of `UserConfigIR` from `user_config` dictionary.
    user_config_ir = UserConfigIR()
    for w in user_config['web_site']:
        alias = w['alias']
        user = w['user']
        id = user['id']
        pw = user['pw']
        blocked_author_memo_pattern = w['blocked_author_memo_pattern']
        blocked_author_name = w['blocked_author_name']

        user_config_for_single_web_site_ir = UserConfigIRForSingleWebSite()
        user_config_for_single_web_site_ir.alias = alias
        user_config_for_single_web_site_ir.user_id = id
        user_config_for_single_web_site_ir.user_pw = pw
        for b in blocked_author_name:
            user_config_for_single_web_site_ir.update_blocked_author_name_set(b)
        user_config_for_single_web_site_ir.blocked_author_memo_pattern = blocked_author_memo_pattern

        # Finally
        user_config_ir.add_entry(alias, user_config_for_single_web_site_ir)

    return user_config_ir


def poll_and_write_bbs(user_config: dict) -> None:
    user_config_ir = build_user_config_ir(user_config)  # An object is created by the callee.

    # TODO(@pastry-personal5): Introduce multiple web sites or objects here.

    # For now, let's do the job for 'c1' web site.
    const_alias = 'c1'
    user_config_ir_for_single_web_site = user_config_ir.get_user_config_ir_for_single_web_site(const_alias)
    if user_config_ir_for_single_web_site:
        obj = C1WebSitePollAndWriter()
        obj.poll_and_write_bbs(user_config_ir_for_single_web_site)
    else:
        logger.error(f'A user config for web site {const_alias} has not been found.')


def read_user_config() -> dict:
    const_user_config_file_path = './main_config.yaml'
    try:
        f = open(const_user_config_file_path, 'r', encoding='utf-8')
        user_config = yaml.load(f.read(), Loader=Loader)
    except IOError:
        logger.error(f'Could not read file: {const_user_config_file_path}')
        return {}
    return user_config


def main():
    user_config = read_user_config()
    if is_valid_user_config(user_config):
        poll_and_write_bbs(user_config)
    else:
        logger.error('Invalid user configuration file.')


if __name__ == '__main__':
    main()
