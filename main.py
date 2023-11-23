# api id 22376755
# api hach  dddf0b68eedb9aa8f1436c8c6cd706a3
import re
import json
import time
import asyncio
from telethon import TelegramClient
from Levenshtein import distance
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_bot_name_from_official_page() -> str:
    options = webdriver.FirefoxOptions()
    # options.headless = True
    driver = webdriver.Firefox(options=options)
    driver.get('http://bibliotecasecreta.nl/')
    # time.sleep(2)  # wait for the page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(By.XPATH, "//aside/img")
    )
    link = driver.find_element(By.XPATH, "//p/a[contains(@onclick, 'brev')]")
    link.click()
    time.sleep(2)
    html = driver.page_source
    driver.quit()
    
    # Utiliza BeautifulSoup para analizar el HTML
    soup = BeautifulSoup(html, 'html.parser')
    try:
        a_tag = soup.find_all("a")[1]
        return a_tag
    except TypeError:
        raise Exception("No Telegram bot name found")
    

print(get_bot_name_from_official_page())

class BibliotecaSecretaBot:
    def __init__(self, api_file_path = './api_file.json') -> None:
        self.api_data = self._load_api_key(api_file_path)
        self.bot_name = asyncio.run(self.get_bot(['Biblioteca', 'Secreta']))
        print(self.bot_name)
        self.epub_name_link_dict = {}
        self.author_name_link_dict = {}

    def _load_api_key(self, api_file_path):
        try:
            with open(api_file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError("API file credentials not found")
    
    async def get_bot(self, keywords_for_search: list):
        keywords_for_search_reversed = keywords_for_search[::-1]
        re_pattern = rf'{'.*' + '.*'.join(keywords_for_search) + '.*' + '|' + '.*' + '.*'.join(keywords_for_search_reversed) + '.*'}'
        try:
            async with TelegramClient('anon', self.api_data['api_id'], self.api_data['api_hash']) as client:
                async for dialog in client.iter_dialogs():
                    if re.search(re_pattern, dialog.title, flags=re.IGNORECASE):
                        return dialog.entity.username
                else:
                    return get_bot_name_from_official_page()
        except ConnectionError:
            raise ConnectionError('Cannot connect to Telegram servers. Please check your internet connection and try again.')
    
    async def send_message(self, text: str, process_result=True):
        try:
            message = None
            async with TelegramClient('anon', self.api_data['api_id'], self.api_data['api_hash']) as client:
                await client.send_message(self.bot_name, text)
                if process_result:
                    message = (await client.get_messages(self.bot_name, limit=1))[0]
            if message:
                if '[' in message.message:
                    await self.process_author()
                elif '/' in message.message:
                    await self.process_title()
        except ConnectionError:
            raise ConnectionError('Cannot connect to Telegram servers. Please check your internet connection and try again.')
    
    async def process_author(self):
        def is_author(authors: dict) -> bool:
            an_author = list(authors.keys())[0]
            return True if '[' in an_author else False
        
        self.author_name_link_dict = await self._process_result()
        
        return self.author_name_link_dict if is_author(self.author_name_link_dict) else None
    
    async def process_title(self):
        def is_title(titles: dict) -> bool:
            an_author = list(titles.keys())[0]
            return True if not '[' in an_author else False
        
        self.epub_name_link_dict  = await self._process_result()
        return self.epub_name_link_dict if is_title(self.epub_name_link_dict) else None
    
                        
    async def _process_result(self):
        try:
            message = None
            async with TelegramClient('anon', self.api_data['api_id'], self.api_data['api_hash']) as client:
                message = (await client.get_messages(self.bot_name, limit=1))[0]
            if message:
                return await self._parsing_message(message) if '/' in message.message else None
        except ConnectionError:
            raise ConnectionError('Cannot connect to Telegram servers. Please check your internet connection and try again.')
    
    async def _parsing_message(self, message):
        result_dict = {}; old_message_str = ''
        message.click(0)
        while message.message != old_message_str:
            links = re.findall(r'/\w+', message.message)
            if not links:
                raise Exception("No links found in message")
            result_dict = {
            line.split('[')[0].strip(): links.pop(0) 
            for line in message.message.split('\n') 
            if '[' in line and ']' in line
            }
            result_dict = {
            line.split('/')[0].strip(): links.pop(0) 
            for line in message.message.split('\n')
            if not '[' in line
            }
            old_message_str = message.message
            await message.click(3)
            async with TelegramClient('anon', self.api_data['api_id'], self.api_data['api_hash']) as client:
                message = (await client.get_messages(self.bot_name, limit=1))[0]
        return result_dict
    
    def most_similar_string(self, string_list, target_string, threshold: int = 15) -> str:
        min_distance = 9999
        most_similar_string = ''
        for string in string_list:
            current_distance = distance(string, target_string)
            if current_distance < min_distance and current_distance < threshold:
                min_distance = current_distance
                most_similar_string = string
        return most_similar_string

    def get_author_by_name(self, name: str) -> str:
        return asyncio.run(self._get_author_by_name(name))
    
    async def _get_author_by_name(self, name: str) -> str:
        await self.send_message(name, process_result=True)
        epub_name = self.most_similar_string(list(self.author_name_link_dict.keys()), name)
        if epub_name:
            link = self.author_name_link_dict[epub_name]
            await self.send_message(link, process_result=False)
            return link
        else:
            raise Exception(f"Author with name {name} not found")
    
    def get_epub_by_name(self, name: str) -> str:
        return asyncio.run(self._get_epub_by_name(name))
    
    def download_ebook(self, author: str, title: str):
        asyncio.run(self._get_author_by_name(author))
        asyncio.run(self._get_epub_by_name(title))
        
    async def _get_epub_by_name(self, name: str):
        try:
            message = None
            await self.process_title()
            epub_name = self.most_similar_string(list(self.epub_name_link_dict.keys()), name)
            if epub_name:
                link = self.epub_name_link_dict[epub_name]
                await self.send_message(link, process_result= False)
                async with TelegramClient('anon', self.api_data['api_id'], self.api_data['api_hash']) as client:
                        message = (await client.get_messages(self.bot_name, limit=1))[0]
                        await message.click(1, 0)
            if message:
                await self.download_epub_from_last_message()
                return message.message
            else:
                raise Exception(f"Ebook with name {name} not found")
        except ConnectionError:
            raise ConnectionError('Cannot connect to Telegram servers. Please check your internet connection and try again.')
            

    async def download_epub_from_last_message(self):
        try:
            async with TelegramClient('anon', self.api_data['api_id'], self.api_data['api_hash']) as client:
                message = (await client.get_messages(self.bot_name, limit=1))[0]
                if message.document and message.document.mime_type == 'application/epub+zip':
                    await message.download_media()
        except ConnectionError:
            raise ConnectionError('Cannot connect to Telegram servers. Please check your internet connection and try again.')
        
# async def download_epub_from_name(self):

# bs = BibliotecaSecretaBot()
# bs.download_ebook('Brandon Sanderson', 'El Imperio Final')
# asyncio.run(bs.find('/aNpVIlvkp'))
# asyncio.run(bs.download_epub_from_last_message())
# # bs.get_author_by_name('Brandon Sanderson')
# bs.get_epub_by_name('El Imperio Final')