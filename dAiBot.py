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

logging.basicConfig(level=logging.DEBUG)


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

async def crawl_naver_cafe_hot_posts(cafe_alias):
    if cafe_alias not in myFile.NAVER_CAFE_LIST:
        return None, f"'{cafe_alias}'은(는) 등록된 카페가 아닙니다."
    
    cafe_info = myFile.NAVER_CAFE_LIST[cafe_alias]
    cafe_id = cafe_info['id']  # 문자열 ID (예: 'dieselmania')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://cafe.naver.com/',
        'Connection': 'keep-alive'
    }
    
    try:
        hot_posts = []
        
        # 1. 모바일 인기글 페이지 시도 (가장 성공률 높음)
        mobile_best_url = f"https://m.cafe.naver.com/{cafe_id}/ArticleList.nhn?search.boardtype=L"
        logging.info(f"Trying mobile best URL: {mobile_best_url}")
        
        try:
            response = requests.get(mobile_best_url, headers=headers)
            logging.info(f"Mobile best URL response status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 모바일 버전의 여러 구조 시도
                article_list = (soup.select('.lst-article li') or 
                                soup.select('.list_area li') or 
                                soup.select('.article_list li') or
                                soup.select('ul.board_list li') or
                                soup.select('.article-list li'))
                
                for article in article_list[:myFile.HOT_POSTS_COUNT]:
                    try:
                        title_elem = (article.select_one('.tit') or 
                                     article.select_one('.txt_area') or 
                                     article.select_one('h3') or
                                     article.select_one('.board_txt') or
                                     article.select_one('.txt'))
                        
                        link_elem = article.select_one('a')
                        
                        if not title_elem or not link_elem:
                            continue
                            
                        title = title_elem.get_text().strip()
                        if not title:
                            continue
                            
                        article_link = link_elem.get('href')
                        if not article_link:
                            continue
                            
                        # 링크 정규화
                        if '/ArticleRead.nhn?' in article_link:
                            # 게시글 ID 추출
                            article_id = None
                            articleid_match = re.search(r'articleid=(\d+)', article_link)
                            if articleid_match:
                                article_id = articleid_match.group(1)
                                article_link = f"https://cafe.naver.com/{cafe_id}/{article_id}"
                            else:
                                if not article_link.startswith('http'):
                                    if article_link.startswith('/'):
                                        article_link = f"https://m.cafe.naver.com{article_link}"
                                    else:
                                        article_link = f"https://m.cafe.naver.com/{article_link}"
                        elif not article_link.startswith('http'):
                            if article_link.startswith('/'):
                                article_link = f"https://m.cafe.naver.com{article_link}"
                            else:
                                article_link = f"https://m.cafe.naver.com/{article_link}"
                        
                        # 조회수 추출 시도
                        view_count_elem = (article.select_one('.num') or 
                                         article.select_one('.view_count') or 
                                         article.select_one('.view_info') or
                                         article.select_one('.view'))
                        
                        view_count = view_count_elem.get_text().strip() if view_count_elem else "알 수 없음"
                        
                        hot_posts.append({
                            'title': title,
                            'link': article_link,
                            'view_count': view_count
                        })
                    except Exception as e:
                        logging.error(f"Error parsing mobile article: {e}", exc_info=True)
                        continue
        except Exception as e:
            logging.error(f"Error accessing mobile site: {e}", exc_info=True)
        
        # 2. PC 인기글 페이지 시도
        if not hot_posts:
            pc_best_url = f"https://cafe.naver.com/{cafe_id}/ArticleList.nhn?search.boardtype=L"
            logging.info(f"Trying PC best URL: {pc_best_url}")
            
            try:
                response = requests.get(pc_best_url, headers=headers)
                logging.info(f"PC best URL response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # iframe URL 추출 시도
                    iframe_src = soup.select_one('#cafe_main')
                    if iframe_src and 'src' in iframe_src.attrs:
                        iframe_url = iframe_src['src']
                        if iframe_url and iframe_url.strip() != "about:blank":
                            if not iframe_url.startswith('http'):
                                if iframe_url.startswith('/'):
                                    iframe_url = f"https://cafe.naver.com{iframe_url}"
                                else:
                                    iframe_url = f"https://cafe.naver.com/{iframe_url}"
                                    
                            logging.info(f"Trying iframe URL: {iframe_url}")
                            
                            try:
                                iframe_response = requests.get(iframe_url, headers=headers)
                                logging.info(f"iframe URL response status: {iframe_response.status_code}")
                                
                                iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                                
                                # 여러 구조 시도
                                article_list = (iframe_soup.select('.article-board tbody tr') or 
                                              iframe_soup.select('#main-area .board-list tbody tr') or
                                              iframe_soup.select('.board-box tbody tr'))
                                
                                for article in article_list[:myFile.HOT_POSTS_COUNT]:
                                    try:
                                        title_elem = (article.select_one('a.article') or 
                                                     article.select_one('.article') or
                                                     article.select_one('.link'))
                                        
                                        if not title_elem:
                                            continue
                                            
                                        title = title_elem.get_text().strip()
                                        if not title:
                                            continue
                                        
                                        article_link = title_elem.get('href')
                                        if not article_link:
                                            continue
                                            
                                        # 게시글 ID 추출 및 링크 정규화
                                        if 'articleid=' in article_link:
                                            article_id = re.search(r'articleid=(\d+)', article_link).group(1)
                                            article_link = f"https://cafe.naver.com/{cafe_id}/{article_id}"
                                        elif not article_link.startswith('http'):
                                            article_link = f"https://cafe.naver.com{article_link}"
                                        
                                        # 조회수 추출
                                        view_count_elem = (article.select_one('.view-count') or 
                                                         article.select_one('.board-count') or 
                                                         article.select_one('.td_view'))
                                        
                                        view_count = view_count_elem.get_text().strip() if view_count_elem else "알 수 없음"
                                        
                                        hot_posts.append({
                                            'title': title,
                                            'link': article_link,
                                            'view_count': view_count
                                        })
                                    except Exception as e:
                                        logging.error(f"Error parsing PC article: {e}", exc_info=True)
                                        continue
                            except Exception as e:
                                logging.error(f"Error accessing iframe: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"Error accessing PC site: {e}", exc_info=True)
        
        # 3. 새로운 모바일 카페 구조 시도
        if not hot_posts:
            new_mobile_url = f"https://m.cafe.naver.com/ca-fe/web/{cafe_id}/home"
            logging.info(f"Trying new mobile URL: {new_mobile_url}")
            
            try:
                response = requests.get(new_mobile_url, headers=headers)
                logging.info(f"New mobile URL response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 새 모바일 구조에서 인기글 추출 시도
                    article_list = (soup.select('.ArticleItem') or 
                                  soup.select('.ArticleListItem') or
                                  soup.select('.article_item'))
                    
                    for article in article_list[:myFile.HOT_POSTS_COUNT]:
                        try:
                            title_elem = (article.select_one('.ArticleTitle') or 
                                       article.select_one('.article_title') or
                                       article.select_one('.title'))
                            
                            link_elem = article.select_one('a')
                            
                            if not title_elem or not link_elem:
                                continue
                                
                            title = title_elem.get_text().strip()
                            if not title:
                                continue
                                
                            article_link = link_elem.get('href')
                            if not article_link:
                                continue
                                
                            # 링크 정규화
                            if not article_link.startswith('http'):
                                # article ID 추출 시도
                                article_id_match = re.search(r'/(\d+)($|\?)', article_link)
                                if article_id_match:
                                    article_id = article_id_match.group(1)
                                    article_link = f"https://cafe.naver.com/{cafe_id}/{article_id}"
                                else:
                                    if article_link.startswith('/'):
                                        article_link = f"https://m.cafe.naver.com{article_link}"
                                    else:
                                        article_link = f"https://m.cafe.naver.com/{article_link}"
                            
                            # 조회수 추출
                            view_count_elem = (article.select_one('.ViewCount') or 
                                             article.select_one('.view_count') or
                                             article.select_one('.count'))
                            
                            view_count = view_count_elem.get_text().strip() if view_count_elem else "알 수 없음"
                            
                            hot_posts.append({
                                'title': title,
                                'link': article_link,
                                'view_count': view_count
                            })
                        except Exception as e:
                            logging.error(f"Error parsing new mobile article: {e}", exc_info=True)
                            continue
            except Exception as e:
                logging.error(f"Error accessing new mobile structure: {e}", exc_info=True)
        
        # 4. 새로운 API 시도 (일부 카페만 지원)
        if not hot_posts:
            feed_api_url = f"https://cafe.naver.com/ca-fe/home/feed/contents/feed-items?cafeId={cafe_id}"
            logging.info(f"Trying feed API URL: {feed_api_url}")
            
            try:
                api_headers = headers.copy()
                api_headers['X-Cafe-Product'] = 'pc'
                api_headers['Content-Type'] = 'application/json'
                
                api_response = requests.get(feed_api_url, headers=api_headers)
                logging.info(f"Feed API response status: {api_response.status_code}")
                
                if api_response.status_code == 200:
                    try:
                        data = api_response.json()
                        
                        if 'message' in data and 'result' in data['message']:
                            items = data['message']['result'].get('feedItems', [])
                            
                            for item in items[:myFile.HOT_POSTS_COUNT]:
                                try:
                                    article = item.get('contentSummary', {})
                                    article_id = article.get('articleId')
                                    title = article.get('subject', '').strip()
                                    view_count = str(article.get('readCount', '알 수 없음'))
                                    
                                    if not title or not article_id:
                                        continue
                                        
                                    article_link = f"https://cafe.naver.com/{cafe_id}/{article_id}"
                                    
                                    hot_posts.append({
                                        'title': title,
                                        'link': article_link,
                                        'view_count': view_count
                                    })
                                except Exception as e:
                                    logging.error(f"Error parsing feed API item: {e}", exc_info=True)
                                    continue
                    except Exception as e:
                        logging.error(f"Error parsing feed API response: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"Error accessing feed API: {e}", exc_info=True)
        
        # 결과 처리
        if not hot_posts:
            logging.warning(f"No posts found for cafe {cafe_alias}")
            return None, f"{cafe_info['description']} 카페에서 인기글을 찾을 수 없습니다. 비공개 카페이거나 로그인이 필요한 카페일 수 있습니다."
        
        # 중복 제거
        unique_posts = []
        seen_titles = set()
        
        for post in hot_posts:
            if post['title'] not in seen_titles:
                seen_titles.add(post['title'])
                unique_posts.append(post)
                
                if len(unique_posts) >= myFile.HOT_POSTS_COUNT:
                    break
        
        return unique_posts, None
        
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
        embed = discord.Embed(title="쇼핑 검색 결과", description=response, color=0xFF00FF)
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
        
        hot_posts, error = await crawl_naver_cafe_hot_posts(키워드)
        
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
                    color=0x800080
                )
                await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f"{cafe_name} 인기글 Top {len(hot_posts)}",
                description=response,
                color=0x800080
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