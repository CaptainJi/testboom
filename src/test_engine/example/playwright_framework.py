#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/7/12 下午6:12
@Author  : CaptainJi
@File    : playwright_framework.py
@Software: PyCharm
"""

import json
import os
import time
from datetime import datetime
from pprint import pprint

from playwright.sync_api import sync_playwright
from src.logger.logger import logger
from src.config import settings


class WebAutoFrameWork:
    """
    Playwright 框架
    """

    def __init__(self):
        self.data_timestamp = None
        self.path = None
        self.timestamp = None
        self.mark_file_name = None
        self.screenshot_file_name = None
        self.screen_shot = None
        self.mark_data = None
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.is_browser_closed = True  # 初始状态设置为 True，表示浏览器是关闭的
        self.auth_file = None

    def init(self):
        if (
            self.browser is None or self.is_browser_closed
        ):  # 检查浏览器是否未初始化或已关闭
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                channel="chrome", headless=False, args=["--start-maximized"]
            )
            self.context = self.browser.new_context(no_viewport=True)
            self.page = self.context.new_page()
            self.is_browser_closed = False  # 更新状态，表示浏览器现在是打开的
        self.page.wait_for_timeout(5000)
        self.page.wait_for_load_state("networkidle")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(settings.DATA_DIR, self.timestamp)
        self.auth_file = os.path.join(self.path, "auth.json")
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def close_browser(self):
        if self.browser and not self.is_browser_closed:  # 确保浏览器已初始化且未关闭
            self.browser.close()
            self.is_browser_closed = True  # 更新状态，表示浏览器现在是关闭的

    # 刷新页面
    def refresh(self):
        """
        刷新页面
        :return:
        """
        self.page.reload()

    def open(self, url):
        """
        打开指定url
        :param url:
        :return:
        """

        self.init()
        self.page.goto(url)
        # 页面最大化
        self.load_auth_info()
        js_path = os.path.join(os.path.dirname(__file__), "page_mark.js")
        self.inject_js(js_path)
        self.save_auth_info()

        return self.get_mark_info()

    def save_auth_info(self):
        """保存鉴权信息到本地文件"""
        storage_state = self.context.storage_state()
        with open(self.auth_file, 'w') as f:
            json.dump(storage_state, f)

    def load_auth_info(self):
        """加载本地保存的鉴权信息"""
        if os.path.exists(self.auth_file):
            with open(self.auth_file, 'r') as f:
                storage_state = json.load(f)
            self.context = self.browser.new_context(storage_state=storage_state)
            self.page = self.context.new_page()
            return True
        else:
            return False

    def source(self):
        """
        获取网页源码
        :return:
        """
        return self.page.content()

    def mouse_move(self, x, y):
        """
        移动鼠标到指定位置
        :param x:
        :param y:
        :return:
        """
        self.page.mouse.move(x, y)

    def mouse_click(self, x, y):
        """
        单击鼠标
        :param x:
        :param y:
        :return:
        """
        self.page.mouse.click(x, y)
        return self.get_mark_info()

    def input_text(self, x, y, text):
        """
        输入文本
        :param x:
        :param y:
        :param text:
        :return:
        """
        self.page.mouse.click(x, y)
        self.page.keyboard.type(text)
        return self.get_mark_info()

    def mouse_db_click(self, x, y):
        """
        双击鼠标
        :param x:
        :param y:
        :return:
        """
        self.page.mouse.dblclick(x, y)
        return self.get_mark_info()

    def select_option(self, x, y, option):
        """
        选择下拉框
        :param x:
        :param y:
        :param option:
        :return:
        """
        self.page.mouse.click(x, y)
        self.page.select_option(option)
        return self.get_mark_info()

    def inject_js(self, inject_js=None):
        """
        注入js并将标注数据保存返回
        :param inject_js:
        :return:
        """
        if inject_js:
            with open(inject_js, 'r', encoding='utf-8') as file:
                content = file.read()
                self.page.wait_for_timeout(5000)
                marked_data = self.page.evaluate(f"{content} markPage();")
        else:
            self.page.wait_for_timeout(5000)
            marked_data = self.page.evaluate("markPage();")

        return marked_data

    def _save_mark(self, timestamp):
        """
        保存标注数据至本地
        :return:
        """
        filename = f"mark_{timestamp}.json"
        if self.mark_data:
            with open(os.path.join(self.path, filename), 'w', encoding='utf-8') as f:
                json.dump(self.mark_data, f, ensure_ascii=False, indent=4)
            self.mark_file_name = filename
        else:
            logger.error("标注不存在")

    def _save_screen_shot(self, timestamp):
        """
        保存截图至本地
        :return:
        """
        self.screen_shot = self.page.screenshot()
        if self.screen_shot:
            filename = f"screenshot_{timestamp}.png"
            path = os.path.join(self.path, filename)
            with open(path, 'wb') as f:
                f.write(self.screen_shot)
            self.screenshot_file_name = filename
            return path
        else:
            logger.error("截图不存在")
            return None

    def get_mark_info(self, save_mark_file=False):
        """
        获取页面标注信息
        :param save_mark_file: 是否保存标注
        :return:
        """
        self.page.evaluate("unmarkPage();")
        self.data_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.mark_data = self.inject_js()
        # self.mark_data = self._trim_mark_info(self.mark_data)
        if save_mark_file:
            self._save_mark(self.data_timestamp)
        return self.mark_data

    def capture_screen_shot(self, data_timestamp=None):
        """
        截图
        :return: self._save_screen_shot()
        """
        if data_timestamp:
            return self._save_screen_shot(data_timestamp)
        else:
            return self._save_screen_shot(self.data_timestamp)

    def _trim_mark_info(self, mark_data):
        """
        精简标注信息
        :param mark_data: 原标注信息
        :return: 精简后的标注信息
        """
        from untils.comm import num_tokens_from_string

        mark_data_str = json.dumps(mark_data)  # Convert dictionary to JSON string
        mark_data_items = list(mark_data.items())  # Convert dictionary to list of items
        while num_tokens_from_string(mark_data_str) >= 5800:
            mark_data_items = mark_data_items[:-1]  # Trim the last item
            mark_data = dict(mark_data_items)  # Convert back to dictionary
            mark_data_str = json.dumps(mark_data)  # Update JSON string after trimming
        return mark_data


if __name__ == '__main__':
    # from src.oss_upload_file import get_upload_url, upload_file, get_file_url
    # from untils.MMLLM import simple_multimodal_conversation_call
    #
    # DASHSCOPE_API_KEY = 'sk-394f8b82326a4ffdbdcfe925121d4cb5'
    # os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY

    web = WebAutoFrameWork()
    web.init()
    web.open("https://www.baidu.com")
    web.get_mark_info()
    web.input_text(588, 210, '极视角')
    web.get_mark_info(save_mark_file=True)
    web.mouse_click(781, 35)
    time.sleep(20)

    # time.sleep(160)
    # image_path = os.path.join(settings.SCREEN_SHOT_DIR, web.screenshot_file_name)
    # mark_path = os.path.join(settings.MARK_FILE_DIR, web.mark_file_name)
    # simple_multimodal_conversation_call(image_path, mark_path)

    # url = get_upload_url(file_name)
    # upload_file(url, file_name)
    # get_file_url(file_name)
    # web.save_mark()
    # web.mouse_click(1163, 30.5)
