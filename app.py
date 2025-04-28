# app.py
from flask import Flask, render_template, Response
import requests
from bs4 import BeautifulSoup
import csv
from io import StringIO
import datetime
import re

app = Flask(__name__)

def scrape_businesstoday_tech_news():
    url = "https://www.businesstoday.in/technology/news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    news_items = []
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Print the first part of the HTML to debug
            print("HTML preview:", soup.prettify()[:500])
            
            # Try several different selectors that might work
            articles = soup.find_all('div', class_=re.compile('story'))
            if not articles:
                articles = soup.find_all('div', class_=re.compile('article'))
            if not articles:
                articles = soup.find_all('li', class_=re.compile('story'))
            if not articles:
                articles = soup.select('.story-listing, .widget-listing, .article-box')
            
            print(f"Found {len(articles)} articles")
            
            if not articles:
                # If we couldn't find articles with class patterns, try looking for article tags
                articles = soup.find_all('article')
                print(f"Found {len(articles)} article tags")
            
            for article in articles:
                try:
                    # Try different selectors for title
                    title_element = article.find('h2') or article.find('h3') or article.find('h1')
                    
                    if title_element:
                        title = title_element.text.strip()
                    else:
                        # Skip if we can't find a title
                        continue
                    
                    # Get the link - try to find the first anchor tag
                    link_element = article.find('a')
                    if link_element and link_element.has_attr('href'):
                        link = link_element['href']
                        if not link.startswith('http'):
                            link = 'https://www.businesstoday.in' + link
                    else:
                        link = '#'
                    
                    # Try to find description/summary
                    description_element = article.find('p') or article.find('div', class_=re.compile('summary|desc|excerpt'))
                    description = "No description available"
                    if description_element:
                        description = description_element.text.strip()
                    
                    # Try to find date
                    date_element = article.find(text=re.compile(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}')) or \
                                  article.find('span', class_=re.compile('date|time')) or \
                                  article.find('div', class_=re.compile('date|time'))
                    
                    date = "No date available"
                    if date_element:
                        if isinstance(date_element, str):
                            date = date_element.strip()
                        else:
                            date = date_element.text.strip()
                    
                    # Add to our list
                    news_items.append({
                        'title': title,
                        'link': link,
                        'description': description,
                        'date': date
                    })
                    
                    print(f"Added article: {title[:30]}...")
                    
                except Exception as e:
                    print(f"Error parsing article: {e}")
            
            if not news_items:
                # Fallback to a more generic approach if no articles found
                all_links = soup.select('a[href*="/technology/"]')
                for link in all_links[:10]:  # Limit to first 10 links
                    try:
                        href = link['href']
                        if not href.startswith('http'):
                            href = 'https://www.businesstoday.in' + href
                            
                        title = link.text.strip()
                        if title and len(title) > 10:  # Ensure it's likely a real title
                            news_items.append({
                                'title': title,
                                'link': href,
                                'description': "Click to read more",
                                'date': "Recent"
                            })
                    except Exception as e:
                        print(f"Error with fallback approach: {e}")
        else:
            print(f"Failed to fetch page: Status code {response.status_code}")
            news_items.append({
                'title': f"Error: Status code {response.status_code}",
                'link': '#',
                'description': "Could not fetch data from the website",
                'date': datetime.datetime.now().strftime("%Y-%m-%d")
            })
            
    except Exception as e:
        print(f"Error connecting to website: {e}")
        news_items.append({
            'title': "Error connecting to the website",
            'link': '#',
            'description': str(e),
            'date': datetime.datetime.now().strftime("%Y-%m-%d")
        })
    
    return news_items

@app.route('/')
def index():
    news_items = scrape_businesstoday_tech_news()
    return render_template('index.html', news_items=news_items)

@app.route('/download-csv')
def download_csv():
    news_items = scrape_businesstoday_tech_news()
    
    # Create a CSV in memory
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Title', 'Description', 'Date', 'Link'])
    
    for item in news_items:
        writer.writerow([
            item['title'],
            item['description'],
            item['date'],
            item['link']
        ])
    
    output = si.getvalue()
    
    # Create response with CSV file
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"businesstoday_tech_news_{current_date}.csv"
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

if __name__ == '__main__':
    app.run(debug=True)