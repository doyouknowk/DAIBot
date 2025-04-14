import discord
import requests
import logging
import os
import json
import random
import datetime
import myFile
import re
from discord import app_commands
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from collections import Counter
from collections import defaultdict
from datetime import datetime


# Discord Bot 클라이언트 생성
DISCORD_BOT_KEY = os.environ['DISCORD_BOT_KEY']
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# YouTube API 설정
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# NAVER API 설정
NAVER_CLIENT_ID = os.environ['NAVER_CLIENT_ID']
NAVER_CLIENT_SECRET = os.environ['NAVER_CLIENT_SECRET']

# NAVER 로그인 계정
NAVER_ID = os.environ['NAVER_ID']
NAVER_PW = os.environ['NAVER_PW']

logging.basicConfig(level=logging.DEBUG)


# NAVER 로그인
def naver_login(session, id, pw):
    try:
        # 로그인 페이지 접속
        login_url = "https://nid.naver.com/nidlogin.login"
        
        # 로그인 페이지 요청
        response = session.get(login_url)
        
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 로그인 데이터 준비
        login_data = {
            'url': 'https://www.naver.com/',
            'svc': '',
            'viewtype': '1',
            'locale': 'ko_KR',
            'postDataKey': '',
            'enctp': '1',
            'smart_LEVEL': '-1',
            'id': id,
            'pw': pw
        }
        
        # 추가 필요한 필드 찾기
        for input_tag in soup.find_all('input'):
            input_name = input_tag.get('name')
            input_value = input_tag.get('value', '')
            
            # 중요한 hidden 필드 추가
            if input_name and input_name not in login_data and input_name not in ['id', 'pw']:
                login_data[input_name] = input_value
        
        # 로그인 시도
        login_headers = {
            'Referer': login_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        login_response = session.post(login_url, data=login_data, headers=login_headers)
        
        # 로그인 성공 여부 확인
        if "로그인" in login_response.text and "비밀번호" in login_response.text:
            logging.error("네이버 로그인 실패")
            return False
        
        # 로그인 후 리다이렉트된 URL 확인
        if "https://nid.naver.com/login/sso/finalize.nhn" in login_response.url:
            # SSO 로그인 처리
            for i in range(2):
                if "https://nid.naver.com/login/sso/finalize.nhn" in login_response.url:
                    redirect_url = re.search(r'location\.replace\("([^"]+)"\)', login_response.text)
                    if redirect_url:
                        next_url = redirect_url.group(1)
                        login_response = session.get(next_url)
        
        # 최종 확인
        check_url = "https://cafe.naver.com/CafeServlet.nhn"
        check_response = session.get(check_url)
        
        # 로그인 확인을 위한 네이버 ID 체크
        if id.lower() in check_response.text.lower():
            logging.info("네이버 로그인 성공")
            return True
        else:
            # 두 번째 체크 방법
            check_main = session.get("https://www.naver.com")
            if 'logout' in check_main.text.lower() or '로그아웃' in check_main.text:
                logging.info("네이버 로그인 성공 (메인 페이지 확인)")
                return True
            
            logging.error("네이버 로그인 실패")
            return False
            
    except Exception as e:
        logging.error(f"네이버 로그인 중 오류 발생: {e}", exc_info=True)
        return False

# NAVER 뉴스 검색
async def search_naver_news(keyword):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "sort": "date",
        "display": 3
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = json.loads(response.text)
        return data.get('items', [])
    else:
        return None

# NAVER 블로그 검색
async def search_naver_blog(keyword):
    url = "https://openapi.naver.com/v1/search/blog.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "sort": "sim",
        "display": 3
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = json.loads(response.text)
        return data.get('items', [])
    else:
        return None

# NAVER 카페 검색       
async def search_naver_cafe(keyword):
    url = "https://openapi.naver.com/v1/search/cafearticle.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "sort": "sim",
        "display": 3
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = json.loads(response.text)
        return data.get('items', [])
    else:
        return None

# NAVER 쇼핑 검색       
async def search_naver_shop(keyword):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "sort": "sim",
        "display": 5
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = json.loads(response.text)
        return data.get('items', [])
    else:
        return None

# NAVER 인기글 크롤링
async def crawl_naver_cafe_hot_posts(cafe_alias, naver_id=None, naver_pw=None):
    if cafe_alias not in myFile.NAVER_CAFE_LIST:
        return None, f"'{cafe_alias}'은(는) 등록된 카페가 아닙니다."
    
    cafe_info = myFile.NAVER_CAFE_LIST[cafe_alias]
    numeric_cafe_id = cafe_info['numeric_id']
    
    # 세션 생성
    session = requests.Session()
    
    # 기본 헤더 설정 - 더 현실적인 브라우저 환경 모방
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'sec-ch-ua': '"Google Chrome";v="121", "Not A(Brand";v="99", "Chromium";v="121"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1'
    }
    
    try:
        # 방법 1: 모바일 페이지 접근 (인기글 탭)
        mobile_url = f"https://m.cafe.naver.com/ca-fe/{cafe_info['id']}?tab=popular"
        logging.info(f"Accessing mobile popular page: {mobile_url}")
        
        mobile_headers = headers.copy()
        mobile_headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.0.0 Mobile/15E148 Safari/604.1'
        
        mobile_response = session.get(mobile_url, headers=mobile_headers)
        logging.info(f"Mobile page response status: {mobile_response.status_code}")
        
        if mobile_response.status_code == 200:
            mobile_soup = BeautifulSoup(mobile_response.text, 'html.parser')
            
            # 모바일 페이지에서 인기글 목록 찾기
            article_items = mobile_soup.select('li.article_item') or mobile_soup.select('.article_list li')
            
            logging.info(f"Found {len(article_items)} article elements on mobile popular page")
            
            if article_items:
                hot_posts = []
                for idx, article in enumerate(article_items[:myFile.HOT_POSTS_COUNT]):
                    try:
                        # 제목 추출
                        title_elem = article.select_one('.article_title') or article.select_one('.tit') or article.select_one('a')
                        if not title_elem:
                            continue
                            
                        title = title_elem.get_text().strip()
                        
                        # 링크 추출
                        href = title_elem.get('href', '')
                        article_id = ''
                        
                        # 상대 URL을 절대 URL로 변환
                        if href.startswith('/'):
                            article_link = f"https://cafe.naver.com{href}"
                        else:
                            article_link = f"https://cafe.naver.com/{cafe_info['id']}/{href}"
                        
                        # 숫자만 추출하여 ID 가져오기
                        if 'articleid=' in href:
                            article_id = re.search(r'articleid=(\d+)', href).group(1)
                        elif 'articleId=' in href:
                            article_id = re.search(r'articleId=(\d+)', href).group(1)
                        elif re.search(r'/(\d+)(?:\?|$)', href):
                            article_id = re.search(r'/(\d+)(?:\?|$)', href).group(1)
                            
                        if article_id:
                            article_link = f"https://cafe.naver.com/{cafe_info['id']}/{article_id}"
                        
                        # 조회수
                        view_count = "알 수 없음"
                        view_elem = article.select_one('.article_info .view') or article.select_one('.view_count') or article.select_one('.td_view')
                        if view_elem:
                            view_text = view_elem.get_text().strip()
                            view_count = re.search(r'\d+', view_text).group(0) if re.search(r'\d+', view_text) else view_text
                        
                        # 날짜
                        date_info = "알 수 없음"
                        date_elem = article.select_one('.article_info .date') or article.select_one('.td_date')
                        if date_elem:
                            date_info = date_elem.get_text().strip()
                        
                        # 작성자
                        nickname = "알 수 없음"
                        nick_elem = article.select_one('.article_info .nickname') or article.select_one('.p-nick') or article.select_one('.writer')
                        if nick_elem:
                            nickname = nick_elem.get_text().strip()
                        
                        # 댓글 수
                        comment_count = "0"
                        comment_elem = article.select_one('.comment_count') or article.select_one('.cmt') or article.select_one('.comment')
                        if comment_elem:
                            comment_text = comment_elem.get_text().strip()
                            comment_match = re.search(r'\d+', comment_text)
                            if comment_match:
                                comment_count = comment_match.group(0)
                        
                        hot_posts.append({
                            'title': title,
                            'link': article_link,
                            'view_count': view_count,
                            'date': date_info,
                            'author': nickname,
                            'comment_count': comment_count
                        })
                    except Exception as e:
                        logging.error(f"Error parsing mobile article {idx}: {e}", exc_info=True)
                        continue
                
                if hot_posts:
                    return hot_posts, None
        
        # 방법 2: PC 페이지 인기글 탭 직접 접근
        pc_url = f"https://cafe.naver.com/f-e/cafes/{numeric_cafe_id}/popular"
        logging.info(f"Accessing PC popular page: {pc_url}")
        
        pc_response = session.get(pc_url, headers=headers)
        logging.info(f"PC popular page response status: {pc_response.status_code}")
        
        if pc_response.status_code == 200:
            pc_soup = BeautifulSoup(pc_response.text, 'html.parser')
            
            # iframe URL 찾기
            iframe = pc_soup.select_one('#cafe_main')
            
            if iframe and iframe.get('src'):
                iframe_src = iframe.get('src')
                if iframe_src:
                    # URL 형식에 따른 처리
                    if iframe_src.startswith('//'):
                        iframe_url = f"https:{iframe_src}"
                    elif iframe_src.startswith('http'):
                        iframe_url = iframe_src
                    else:
                        iframe_url = f"https://cafe.naver.com{iframe_src}"
                    
                    logging.info(f"Found iframe URL: {iframe_url}")
                    
                    iframe_response = session.get(iframe_url, headers=headers)
                else:
                    logging.error("No src attribute found in iframe")
                    return None, "iframe의 src 속성을 찾을 수 없습니다."
                
                if iframe_response.status_code == 200:
                    iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                    
                    # 테이블 형식의 게시글 목록 찾기
                    article_rows = iframe_soup.select('.article-board .list-type-h tbody tr:not(.notice)') or \
                                  iframe_soup.select('.article-board table tbody tr') or \
                                  iframe_soup.select('.board-box') or \
                                  iframe_soup.select('li.article-list')
                    
                    logging.info(f"Found {len(article_rows)} article elements in iframe")
                    
                    if article_rows:
                        hot_posts = []
                        for idx, article in enumerate(article_rows[:myFile.HOT_POSTS_COUNT]):
                            try:
                                # 제목 추출
                                title_elem = article.select_one('.article') or article.select_one('a.article-title') or article.select_one('.subject a')
                                if not title_elem:
                                    continue
                                    
                                title = title_elem.get_text().strip()
                                href = title_elem.get('href', '')
                                
                                # 상대 URL을 절대 URL로 변환
                                article_id = ''
                                
                                # ID 추출
                                if re.search(r'articleid=(\d+)', href):
                                    article_id = re.search(r'articleid=(\d+)', href).group(1)
                                elif re.search(r'articleId=(\d+)', href):
                                    article_id = re.search(r'articleId=(\d+)', href).group(1)
                                elif re.search(r'/(\d+)(?:\?|$)', href):
                                    article_id = re.search(r'/(\d+)(?:\?|$)', href).group(1)
                                
                                if article_id:
                                    article_link = f"https://cafe.naver.com/{cafe_info['id']}/{article_id}"
                                else:
                                    if href.startswith('/'):
                                        article_link = f"https://cafe.naver.com{href}"
                                    else:
                                        article_link = f"https://cafe.naver.com/{cafe_info['id']}/{href}"
                                
                                # 조회수
                                view_count = "알 수 없음"
                                view_elem = article.select_one('.view-count') or article.select_one('.td_view')
                                if view_elem:
                                    view_count = view_elem.get_text().strip()
                                
                                # 날짜
                                date_info = "알 수 없음"
                                date_elem = article.select_one('.date') or article.select_one('.td_date')
                                if date_elem:
                                    date_info = date_elem.get_text().strip()
                                
                                # 작성자
                                nickname = "알 수 없음"
                                nick_elem = article.select_one('.nickname') or article.select_one('.p-nick') or article.select_one('.writer')
                                if nick_elem:
                                    nickname = nick_elem.get_text().strip()
                                
                                # 댓글 수
                                comment_count = "0"
                                comment_elem = article.select_one('.cmt') or article.select_one('.comment')
                                if comment_elem:
                                    comment_match = re.search(r'\[(\d+)\]', comment_elem.get_text())
                                    if comment_match:
                                        comment_count = comment_match.group(1)
                                
                                hot_posts.append({
                                    'title': title,
                                    'link': article_link,
                                    'view_count': view_count,
                                    'date': date_info,
                                    'author': nickname,
                                    'comment_count': comment_count
                                })
                            except Exception as e:
                                logging.error(f"Error parsing iframe article {idx}: {e}", exc_info=True)
                                continue
                        
                        if hot_posts:
                            return hot_posts, None
        
        # 방법 3: API 접근 (인기글 탭)
        api_url = f"https://apis.naver.com/cafe-web/cafe2/ArticleListV2Popular.json?search.clubid={numeric_cafe_id}&search.page=1&search.perPage={myFile.HOT_POSTS_COUNT}"
        api_headers = headers.copy()
        api_headers['Accept'] = 'application/json, text/plain, */*'
        api_headers['referer'] = f"https://cafe.naver.com/f-e/cafes/{numeric_cafe_id}/popular"
        
        logging.info(f"Trying Popular API endpoint: {api_url}")
        api_response = session.get(api_url, headers=api_headers)
        
        if api_response.status_code == 200:
            try:
                data = api_response.json()
                if 'message' in data and data['message'].get('result', {}).get('articleList'):
                    articles = data['message']['result']['articleList']
                    
                    hot_posts = []
                    for article in articles[:myFile.HOT_POSTS_COUNT]:
                        try:
                            title = article.get('subject', '')
                            article_id = article.get('articleId', '')
                            article_link = f"https://cafe.naver.com/{cafe_info['id']}/{article_id}"
                            view_count = article.get('readCount', 0)
                            date_info = article.get('writeDateTimestamp', '')
                            
                            # 날짜 형식 변환
                            if date_info:
                                date_obj = datetime.fromtimestamp(date_info / 1000)
                                date_info = date_obj.strftime('%Y.%m.%d.')
                            
                            nickname = article.get('writerNickname', '')
                            comment_count = article.get('commentCount', 0)
                            
                            hot_posts.append({
                                'title': title,
                                'link': article_link,
                                'view_count': str(view_count),
                                'date': date_info,
                                'author': nickname,
                                'comment_count': str(comment_count)
                            })
                        except Exception as e:
                            logging.error(f"Error parsing API article: {e}", exc_info=True)
                            continue
                    
                    if hot_posts:
                        return hot_posts, None
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse API response as JSON: {e}")
        
        # 디버깅을 위해 HTML 저장
        with open('debug_cafe_html.html', 'w', encoding='utf-8') as f:
            f.write(pc_response.text)
        
        logging.error(f"Failed to parse {cafe_info['description']} cafe popular posts. HTML saved to debug_cafe_html.html")
        return None, f"{cafe_info['description']} 카페에서 인기글을 찾을 수 없습니다. 네이버 페이지 구조가 변경되었을 가능성이 높습니다."
        
    except Exception as e:
        logging.error(f"Error crawling cafe hot posts: {e}", exc_info=True)
        return None, f"카페 인기글 크롤링 중 오류가 발생했습니다: {str(e)}"

# YouTube 검색
async def search_youtube(keyword):
    # YouTube 검색 실행
    search_response = youtube.search().list(
        q=keyword,
        type='video',
        part='id,snippet',
        maxResults=3
    ).execute()
    
    return search_response.get('items', [])

@tree.command(name="뉴스", description="네이버 뉴스를 검색합니다.")
async def news_command(interaction: discord.Interaction, 키워드: str):
    logging.info(f"News command received with keyword: {키워드}")
    await interaction.response.defer(thinking=True)
    
    try:
        keywords = 키워드.split(',')
        response = f"{', '.join(keywords)} 관련 최신 뉴스입니다.\n"
    
        for keyword in keywords:
            keyword = keyword.strip()

            logging.info(f"Searching for keyword: {keyword}")

            news = await search_naver_news(keyword)

            if news:
                response += f"\n\n키워드: {keyword}\n"
                for item in news[:3]:
                    title = item['title'].replace("<b>", "").replace("</b>", "")
                    pubDate = datetime.datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
                    pubDate = pubDate.strftime('%Y-%m-%d %H:%M')
                    link = item['link']
                    response += f"\n* 기사: {title}\n* 작성일: {pubDate}\n* 링크: {link}\n"
            else:
                response += f"\n\n키워드 '{keyword}'에 대한 뉴스를 찾을 수 없습니다."

        logging.info(f"Response content: {response}")
        embed = discord.Embed(title="뉴스 검색 결과", description=response, color=0xFFFF00)
        await interaction.followup.send(embed=embed)
    
    except Exception as e:
        logging.error(f"Error in news command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)

@tree.command(name="블로그", description="네이버 블로그를 검색합니다.")
async def blog_command(interaction: discord.Interaction, 키워드: str):
    logging.info(f"Blog command received with keyword: {키워드}")
    await interaction.response.defer(thinking=True)
    
    try:
        keywords = 키워드.split(',')
        response = f"{', '.join(keywords)} 관련 블로그 포스트입니다.\n"
        
        for keyword in keywords:
            keyword = keyword.strip()

            logging.info(f"Searching for keyword: {keyword}")

            blogs = await search_naver_blog(keyword)

            if blogs:
                response += f"\n\n키워드: {keyword}\n"
                for item in blogs[:3]:
                    bloggername = item['bloggername']
                    title = item['title'].replace("<b>", "").replace("</b>", "")
                    link = item['link']
                    response += f"\n* 블로거: {bloggername}\n* 포스트: {title}\n* 링크: {link}\n"
            else:
                response += f"\n\n키워드 '{keyword}'에 대한 블로그 포스트를 찾을 수 없습니다."
        
        logging.info(f"Response content: {response}")
        embed = discord.Embed(title="블로그 검색 결과", description=response, color=0x00FF00)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logging.error(f"Error in blog command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)

@tree.command(name="카페", description="네이버 카페를 검색합니다.")
async def cafe_command(interaction: discord.Interaction, 키워드: str):
    logging.info(f"Cafe command received with keyword: {키워드}")
    await interaction.response.defer(thinking=True)
    
    try:
        keywords = 키워드.split(',')
        response = f"{', '.join(keywords)} 관련 카페 게시글입니다.\n"
        
        for keyword in keywords:
            keyword = keyword.strip()

            logging.info(f"Searching for keyword: {keyword}")

            cafes = await search_naver_cafe(keyword)

            if cafes:
                response += f"\n\n키워드: {keyword}\n"
                for item in cafes[:3]:
                    cafename = item['cafename']
                    title = item['title'].replace("<b>", "").replace("</b>", "")
                    link = item['link']
                    response += f"\n* 카페명: {cafename}\n* 게시글: {title}\n* 링크: {link}\n"
            else:
                response += f"\n\n키워드 '{keyword}'에 대한 카페 게시글을 찾을 수 없습니다."
        
        logging.info(f"Response content: {response}")
        embed = discord.Embed(title="카페 검색 결과", description=response, color=0x0000FF)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logging.error(f"Error in cafe command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)

@tree.command(name="쇼핑", description="네이버 쇼핑을 검색합니다.")
async def shop_command(interaction: discord.Interaction, 키워드: str):
    logging.info(f"Shop command received with keyword: {키워드}")
    await interaction.response.defer(thinking=True)
    
    try:
        keywords = 키워드.split(',')
        response = f"{', '.join(keywords)} 관련 상품입니다.\n"
        
        for keyword in keywords:
            keyword = keyword.strip()

            logging.info(f"Searching for keyword: {keyword}")

            products = await search_naver_shop(keyword)

            if products:
                response += f"\n\n키워드: {keyword}\n"
                for item in products[:5]:
                    title = item['title'].replace("<b>", "").replace("</b>", "")
                    mallName = item['mallName']
                    link = item['link']
                    response += f"\n* 상품명: {title}\n* 스토어: {mallName}\n* 링크: {link}\n"
            else:
                response += f"\n\n키워드 '{keyword}'에 대한 상품을 찾을 수 없습니다."
        
        logging.info(f"Response content: {response}")
        embed = discord.Embed(title="쇼핑 검색 결과", description=response, color=0x800080)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logging.error(f"Error in shop command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)

@tree.command(name="인기글", description="네이버 카페의 실시간 인기글을 확인합니다.")
async def hot_posts_command(interaction: discord.Interaction, 키워드: str):
    logging.info(f"Hot posts command received for cafe: {키워드}")
    await interaction.response.defer(thinking=True)
    
    try:
        # 키워드로 받은 카페가 정의되어 있는지 확인
        if 키워드 not in myFile.NAVER_CAFE_LIST:
            available_cafes = ", ".join(myFile.NAVER_CAFE_LIST.keys())
            await interaction.followup.send(f"'{키워드}'은(는) 등록된 카페가 아닙니다. 사용 가능한 카페: {available_cafes}", ephemeral=True)
            return
            
        cafe_info = myFile.NAVER_CAFE_LIST[키워드]
        cafe_name = cafe_info['description'].split(' (')[0]
        
        # 로그인한 상태로 크롤링
        hot_posts, error = await crawl_naver_cafe_hot_posts(키워드, NAVER_ID, NAVER_PW)
        
        if error:
            await interaction.followup.send(f"오류: {error}", ephemeral=True)
            return
        
        if not hot_posts:
            await interaction.followup.send(f"{cafe_name} 카페에서 인기글을 찾을 수 없습니다.", ephemeral=True)
            return
        
        response = f"{cafe_name} 카페의 실시간 인기글 Top {len(hot_posts)}입니다.\n\n"
        
        for i, post in enumerate(hot_posts, 1):
            response += f"{i}. {post['title']}\n"
            response += f"   조회수: {post['view_count']}\n"
            response += f"   링크: {post['link']}\n\n"
        
        logging.info(f"Response content length: {len(response)}")
        
        # 디스코드 임베드 생성 (길이 제한이 있으므로 필요시 분할)
        if len(response) > 4000:  # 디스코드 임베드 설명 제한은 4096자
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(
                    title=f"{cafe_name} 인기글 Top {myFile.HOT_POSTS_COUNT} ({i+1}/{len(chunks)})",
                    description=chunk,
                    color=0xFF00FF
                )
                await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{cafe_name} 인기글 Top {len(hot_posts)}",
                description=response,
                color=0xFF00FF
            )
            await interaction.followup.send(embed=embed)
    
    except Exception as e:
        logging.error(f"Error in hot_posts command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)

@tree.command(name="유튜브", description="유튜브를 검색합니다.")
async def youtube_command(interaction: discord.Interaction, 키워드: str):
    logging.info(f"YouTube command received with keyword: {키워드}")
    await interaction.response.defer(thinking=True)
    
    try:
        keywords = 키워드.split(',')
        response = f"{', '.join(keywords)} 관련 유튜브 동영상입니다.\n"
        
        for keyword in keywords:
            keyword = keyword.strip()
            
            logging.info(f"Searching for keyword: {keyword}")
            
            videos = await search_youtube(keyword)
            
            if videos:
                response += f"\n\n키워드: {keyword}\n"
                for item in videos[:3]:
                    video_title = item['snippet']['title']
                    channel_title = item['snippet']['channelTitle']
                    video_link = f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                    response += f"\n* 제목: {video_title}\n* 채널명: {channel_title}\n* 링크: {video_link}\n"
            else:
                response += f"\n\n키워드 '{keyword}'에 대한 유튜브 동영상을 찾을 수 없습니다."
        
        logging.info(f"Response content: {response}")
        embed = discord.Embed(title="유튜브 검색 결과", description=response, color=0xFF0000)
        await interaction.followup.send(embed=embed)
    
    except Exception as e:
        logging.error(f"Error in YouTube command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)


# 로또 당첨번호 / 추천번호 추출 START
# 동행복권 사이트에서 최근 회차 당첨번호 가져오기
def get_winning_numbers(count):
    url = "https://www.dhlottery.co.kr/common.do?method=main"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    latest_draw = int(soup.select_one("strong#lottoDrwNo").text)
    
    winning_numbers = []
    for i in range(count):
        draw_number = latest_draw - i
        url = f"https://www.dhlottery.co.kr/gameResult.do?method=byWin&drwNo={draw_number}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        numbers = soup.select("span.ball_645")
        winning_numbers.append((draw_number, [int(num.text) for num in numbers[:6]]))
    
    return winning_numbers

# 최근 n회차 동안 가장 많이 당첨된 번호 k개 추출
def get_most_frequent_numbers():
    all_numbers = []
    for _, numbers in get_winning_numbers(myFile.MOST_WIN_CHECK_TERM):
        all_numbers.extend(numbers)
    number_counts = Counter(all_numbers)
    return number_counts.most_common(myFile.MOST_WIN_NUM_COUNT)

# 해당 번호의 궁합수 찾기
def get_compatibility_numbers():
    winning_numbers = get_winning_numbers(myFile.MOST_WIN_CHECK_TERM)  # 최근 n회차 당첨번호
    compatibility_dict = defaultdict(lambda: defaultdict(int))

    for _, numbers in winning_numbers:
        for i in range(6):
            for j in range(i + 1, 6):
                compatibility_dict[numbers[i]][numbers[j]] += 1
                compatibility_dict[numbers[j]][numbers[i]] += 1

    best_compatibility = {}
    for num in range(1, 46):
        if compatibility_dict[num]:
            best_compatibility[num] = max(compatibility_dict[num], key=compatibility_dict[num].get)
        else:
            best_compatibility[num] = num  # 데이터가 없는 경우 자기 자신을 반환

    return best_compatibility

# 전역 변수로 궁합수 딕셔너리 생성
COMPATIBILITY_NUMBERS = get_compatibility_numbers()

# 계산한 궁합수 반환
def get_compatibility_number(number):
    return COMPATIBILITY_NUMBERS[number]

# 로또 추천번호 생성
def generate_recommended_set(frequent_numbers, compatibility_numbers):
    # 가장 많이 당첨된 번호 k개 중 무작위로 3개 선택
    selected_numbers = random.sample(frequent_numbers, 3)
    
    # 선택된 3개 번호의 궁합수 추가
    set_numbers = selected_numbers.copy()
    for num in selected_numbers:
        compat_num = compatibility_numbers[num]
        if compat_num not in set_numbers:
            set_numbers.append(compat_num)
        else:
            # 궁합수가 이미 선택된 경우, 다른 번호 선택
            remaining_numbers = [n for n in frequent_numbers + list(compatibility_numbers.values())
                                 if n not in set_numbers]
            if remaining_numbers:
                set_numbers.append(random.choice(remaining_numbers))
    
    # 6개의 번호가 될 때까지 나머지 번호 추가
    while len(set_numbers) < 6:
        remaining_numbers = [n for n in frequent_numbers + list(compatibility_numbers.values())
                             if n not in set_numbers]
        if remaining_numbers:
            set_numbers.append(random.choice(remaining_numbers))
    
    return sorted(set_numbers)

@tree.command(name="로또", description="키워드에 '당첨번호' 또는 '추천번호'를 입력하세요. 최근 당첨번호 확인 및 추천번호를 생성합니다.")
async def lotto(interaction: discord.Interaction, 키워드: str):
    if 키워드 not in ["당첨번호", "추천번호"]:
        await interaction.response.send_message("키워드는 '당첨번호' 또는 '추천번호'만 입력 가능합니다.")
        return

    await interaction.response.defer(thinking=True)

    try:
        if 키워드 == "당첨번호":
            winning_numbers = get_winning_numbers(myFile.LAST_WIN_CHECK_TERM)
            response = f"최근 {myFile.LAST_WIN_CHECK_TERM}회차 당첨번호 입니다.\n\n"
            for draw, numbers in winning_numbers:
                response += f"* {draw}회: {' '.join(map(str, numbers))}\n"
        
        elif 키워드 == "추천번호":
            frequent_numbers_with_count = get_most_frequent_numbers()
            frequent_numbers = [num for num, _ in frequent_numbers_with_count]
            compatibility_numbers = {num: get_compatibility_number(num) for num in frequent_numbers}
            
            recommended_sets = [generate_recommended_set(frequent_numbers, compatibility_numbers) for _ in range(myFile.RECOMMEND_SET_COUNT)]
            
            response = f"추천 번호 {myFile.RECOMMEND_SET_COUNT}세트\n\n"
            for i, numbers in enumerate(recommended_sets, 1):
                response += f"* {i}세트: {' '.join(map(str, numbers))}\n"
            
            response += "\n" + "-" * 30 + "\n\n"
            response += f"최근 {myFile.MOST_WIN_CHECK_TERM}회차 동안\n가장 많이 당첨된 번호\n\n"
            for num, count in frequent_numbers_with_count:
                response += f"* {num}  (당첨횟수: {count} / 궁합수: {compatibility_numbers[num]})\n"

        # 처리가 완료된 후 결과를 보냅니다.
        logging.info(f"Response content: {response}")
        embed = discord.Embed(title=f"로또 {키워드} 검색 결과", description=response, color=0xFFA500)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logging.error(f"Error in YouTube command: {e}", exc_info=True)
        await interaction.followup.send("명령어 처리 중 오류가 발생했습니다.", ephemeral=True)
# 로또 당첨번호 / 추천번호 추출 END


@client.event
async def on_ready():
    logging.info(f'{client.user} has connected to Discord!')
    try:
        synced = await tree.sync()
        logging.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logging.error(f"Failed to sync commands: {e}")

client.run(DISCORD_BOT_KEY)