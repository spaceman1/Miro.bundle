import re, string, urllib

MIRO_PREFIX       = "/video/miro"
CACHE_INTERVAL    = 1800
MIRO_URL          = 'http://www.miroguide.com/'
MIRO_API          = 'https://www.miroguide.com/api/'

YOUTUBE_VIDEO_FORMATS = ['Standard', 'Medium', 'High', '720p', '1080p']
YOUTUBE_FMT = [34, 18, 35, 22, 37]

####################################################################################################
def Start():
	Plugin.AddPrefixHandler(MIRO_PREFIX, MainMenu, 'Miro Guide', 'icon-default.png', 'art-default.png')
	Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
	MediaContainer.title1 = 'Miro'
	MediaContainer.content = 'Items'
	MediaContainer.art = R('art-default.png')
	HTTP.CacheTime = CACHE_INTERVAL
	DirectoryItem.thumb = R('icon-default.png')
	VideoItem.thumb = R('icon-default.png')
####################################################################################################
#def UpdateCache():
	# need to figure out best cache plan

####################################################################################################
def MainMenu():
	dir = MediaContainer()
	#dir.Append(Function(DirectoryItem(GetVideosRSS,     title="Staff Picks", thumb=R('staffpicks.png')), name='channels/staffpicks', title2='Staff Picks'))
	#dir.Append(Function(DirectoryItem(FeaturedChannels, title="Featured Channels", thumb=R('featured.png'))))  
	dir.Append(Function(DirectoryItem(Categories, title=L("Categories"))))
	dir.Append(Function(DirectoryItem(Languages, title=L("Languages"))))
	dir.Append(Function(DirectoryItem(GetMiroFeed, title=L("New Channels")), feedUrl='http://feeds.feedburner.com/miroguide/new'))
	dir.Append(Function(DirectoryItem(GetMiroFeed, title=L("Featured Channels")), feedUrl='http://feeds.feedburner.com/miroguide/featured'))
	dir.Append(Function(DirectoryItem(GetMiroFeed, title=L("Popular Channels")), feedUrl='http://feeds.feedburner.com/miroguide/popular'))
	dir.Append(Function(DirectoryItem(GetMiroFeed, title=L("Top Rated Channels")), feedUrl='http://feeds.feedburner.com/miroguide/toprated'))
	dir.Append(Function(DirectoryItem(GetMiroFeed, title=L("HD Channels"), thumb=R('hd.png')), feedUrl='https://www.miroguide.com/rss/tags/HD'))
	dir.Append(Function(InputDirectoryItem(GetMiroFeed, title=L("Search for Feed..."), prompt=L("Search for Feed..."), thumb=R('search.png')), feedUrl='https://www.miroguide.com/rss/search/'))
	return dir
	
####################################################################################################
def Categories(sender, sort='popular'):
	dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
	categories = JSON.ObjectFromURL('https://www.miroguide.com/api/list_categories?datatype=json')
	for category in categories:
		title = category['name']
		dir.Append(Function(DirectoryItem(GetDirectory, title=title), filter='category', filter_value=urllib.quote(title), title2=title, sort=sort))
	return dir

def Languages(sender, sort='popular'):
	dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
	for item in HTML.ElementFromURL('http://miroguide.com/languages/').xpath('//ul[@class="group-list"]/li/a'):
		title = item.text
		dir.Append(Function(DirectoryItem(GetDirectory, title=title), filter='language', filter_value=urllib.quote(title), title2=title, sort=sort))
	return dir
####################################################################################################
def GetDirectory(sender, title2, filter, filter_value, sort='', limit='50'):
	dir = MediaContainer(viewGroup='Details', title2=title2)
	url = MIRO_API + 'get_channels?datatype=json&filter=%s&filter_value=%s&sort=%s' % (filter, filter_value, sort)
	if limit != '':
		url += '&limit=' + limit

	results = JSON.ObjectFromURL(url.replace(' ','+'), cacheTime=0)
	for entry in results:
		title = entry['name']
		subtitle = entry['publisher']
		feedUrl = entry['url']
		if not feedUrl: continue
		if not len(entry['item']): continue
		try: thumb = entry['thumbnail_url']
		except: pass
		summary = entry['description']
		dir.Append(Function(DirectoryItem(GetFeed, title=title, subtitle=subtitle, thumb=thumb, summary=summary), title2=title, feedUrl=feedUrl, folderthumb=thumb))
	return dir
####################################################################################################

def GetMiroFeed(sender, feedUrl, title2='', folderthumb='', query=''):
	dir = MediaContainer(viewGroup='Details', title2=title2)
	feedHtml = HTTP.Request(feedUrl + query.replace(' ', '+'), errors='ignore').content
	encoding = feedHtml.split('encoding="')[1].split('"')[0]
	feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')
	
	feed = RSS.FeedFromString(feedHtml)
	#Log(feed)
	for item in feed['items']:
		#Log(item)
		#soup = BSS(item.title, convertEntities=BSS.HTML_ENTITIES) 
		#title = soup.contents[0]
		title = item.title.replace('&#39;',"'").replace('&amp;','&')
		if isinstance(title, str): # BAD: Not true for Unicode strings!
			try:
				title = title.encode('utf-8','replace') #.encode('utf-8')
			except:
				continue #skip this, it likely will bork
		try:
			date = item.updated
		except:
			date = ''
		subtitle = date
		soup = StripTags(item.description)#, convertEntities=BSS.HTML_ENTITIES
		try:
			summary = soup.contents[0]
		except:
			summary = item.description.encode('utf-8','ignore')
		thumb = item.thumbnail
		feedUrl = item["summary_detail"]["value"].replace('amp;','')
		feedUrl = feedUrl[feedUrl.find('url1=')+5:]
		feedUrl = feedUrl[:feedUrl.find('&trackback1')].replace('%3A',':')
		feddUrl = feedUrl.replace(' ', '%20')
		#Log(feedUrl)

		dir.Append(Function(DirectoryItem(GetFeed, title=title, subtitle=subtitle, thumb=thumb, summary=summary), title2=title, feedUrl=feedUrl, folderthumb=thumb))
	return dir

def GetFeed(sender, feedUrl, title2="", folderthumb=""):
	dir = MediaContainer(viewGroup='Details', title2=title2)
	youTubeCookies = HTTP.GetCookiesForURL('http://www.youtube.com/')
	dir.httpCookies = youTubeCookies
	feedHtml = HTTP.Request(urllib.unquote(feedUrl), errors='ignore').content
	encoding = re.search(r"encoding=([\"'])([^\1]*?)\1", feedHtml).group(2) #'
	feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

	feed = RSS.FeedFromString(feedHtml)
	#Log(feed)
	for item in feed['items']:
		#Log(item)
		duration = ''
		title = item.title.replace('&#39;',"'").replace('&amp;','&')
		if isinstance(title, str): # BAD: Not true for Unicode strings!
			try:
				title = title.encode('utf-8','replace') #.encode('utf-8')
			except:
				continue #skip this, it likely will bork
		#title = item.title.encode('utf-8','ignore')
		#title = item.title.decode('utf-8','ignore')
		#soup = BSS(item.title, convertEntities=BSS.HTML_ENTITIES) 
		#try:
		#  title = soup.contents[0].encode('utf-8')
		#except:
		#  title = ''  
		#Log(type(title))
		try:
			date = item.updated
		except:
			date = ''
		subtitle = date
		soup = StripTags(item.description)#, convertEntities=BSS.HTML_ENTITIES
		try:
			summary = soup.contents[0]
		except:
			summary = item.description.encode('utf-8','ignore')
		try:  
			thumb = item.media_thumbnail
		except: 
			try: 
				thumb = item.thumbnail
			except: thumb = ''
		key = ''
		if item.has_key('enclosures'):
			for enclosure in item["enclosures"]:
				#Log('enclosure:')
				#Log(enclosure)
				key = enclosure['href']
				try:
					duration = enclosure['length']
				except:
					duration = ''
		if key == '':
			key = item.link
		#Log(key)
		if key.count('.torrent') > 0:
			#insert message box re: not supporting torrents here.
			break
		if key.count('.html') > 0:
			continue
		if key.count('youtube') > 0:
			if key.count('watch') == 0:
				key = 'http://www.youtube.com/watch?v=' + key.split('v/')[-1][:11] #http://www.youtube.com/v/hlkDIYxUrpA&amp;amp;hl=en&amp;amp;fs=1
			thumb = 'http://i.ytimg.com/vi/%s/default.jpg' % key.split("=")[-1]
			dir.Append(Function(VideoItem(PlayYouTubeVideo, title, date=date, subtitle=subtitle, desc=summary, thumb=thumb, duration=duration), ext='flv', id=key))
		else:
			if thumb == '':
				thumb = folderthumb
			dir.Append(VideoItem(key, title, date, summary, thumb=thumb))
	return dir

####################################################################################################

def StripTags(str):
	return re.sub(r'<[^<>]+>', '', str)

####################################################################################################
def PlayYouTubeVideo(sender, id):
	yt_page = HTTP.Request(id).content
	fmt_url_map = re.findall('"fmt_url_map".+?"([^"]+)', yt_page)[0]
	fmt_url_map = fmt_url_map.replace('\/', '/').split(',')

	fmts = []
	fmts_info = {}

	for f in fmt_url_map:
		(fmt, url) = f.split('|')
		fmts.append(fmt)
		fmts_info[str(fmt)] = url

	index = 0
	if YOUTUBE_FMT[index] in fmts:
		fmt = YOUTUBE_FMT[index]
	else:
		for i in reversed( range(0, index+1) ):
			if str(YOUTUBE_FMT[i]) in fmts:
				fmt = YOUTUBE_FMT[i]
				break
			else:
				fmt = 5

	url = fmts_info[str(fmt)]
	url = url.replace('\\u0026', '&')
	#Log(url)
	return Redirect(url)
