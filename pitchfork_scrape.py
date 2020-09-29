# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 17:37:17 2020

@author: dschafer
"""

#%% imports
import pandas
import requests
import re
import time
import configparser
import spotipy
import spotipy.util as util
from bs4 import BeautifulSoup as bs

#%% to do list
# TODO: split featured artists where multiple


#%% read config file to get credentials
config = configparser.ConfigParser()
config.read(r'C:\Users\dschafer\Documents\Python Scripts\pitchfork_scrape\pitchfork_scrape.config')

spotify_client_id = config.get('Credentials','spotify_client_id')
spotify_client_secret = config.get('Credentials','spotify_client_secret')



#%% scratch for early prototypes


# base page format for best tracks pages. iterate over page number in the slug
# currently runts up to 243
# root_path = r'https://pitchfork.com/reviews/best/tracks/?page='



# foo = root_path + '120'


# req = requests.get(foo)
# soup = bs(req.text)


# test case to identify 1 artist
# naz = soup.findAll(text=re.compile('FKA'))
# naz[0].parent.parent.parent.parent.parent


# test case to identify top-of-page artist

...

# testing capturing all artists

# zap = soup.find_all(attrs={'class':"track-collection-item__details"})
# bar = zap[2] # 3 has multiple genres

#%% function to get the page contents

def get_best_tracks_page(page_num:int):
    
    # build page url 
    page_url = r'https://pitchfork.com/reviews/best/tracks/?page=' + str(page_num)
    
    # request web page
    req = requests.get(page_url)
    
    # pass it to Beautiful soup for parsing
    soup = bs(req.text, features='lxml')

    return soup

def get_head_track_result(soup):
    """function to get SINGLE track at top of page"""
    
    head_tag = soup.find_all(attrs={'class':"track-hero"})
   
    head_tag = head_tag[0]
        
    return head_tag



def get_body_track_results(soup):
    """ function to get a set of tracks from page body for parsing
    """
    
    body_tag = soup.find_all(attrs={'class':"track-collection-item__details"})
    assert body_tag, 'No body results?!?!!?!'
    
    return body_tag
    

def get_page_track_results(soup):
    """just gets the head tag, then the body tag"""
    
    # a tag object
    head_tag = get_head_track_result(soup)
    
    # a list of tag objects
    body_tags = get_body_track_results(soup)
    
    body_tags.append(head_tag)
    
    return body_tags
    



#%% parse titles from tags
    
# turns out they all work for the structure of the head tag as well.

# works
def parse_body_artist(bar):

    # parse artist name
    artist_box = bar.findChild(attrs={'class': 'artist-list'}).contents
    
    # first listed artist is assumed main
    artist = artist_box[0].getText()

    other_artists=[]
    for i in range(1, len(artist_box)):
        other_artists.append(artist_box[i].getText())
    
    return artist, other_artists

# dnw
def parse_body_title_fa(bar):
    
    # parse title     
    if 'track-hero' in bar.attrs['class']:
        title = bar.findChild(attrs={'class': 'title'}).contents[0]
    else:
        title = bar.findChild(attrs={'class': 'track-collection-item__title'}).contents[0]

    # titles sometimes contain featured artists like: ' [ft Jay-Z]'
    # I need to strip and store these before stripping quotes
    
    # match the featured artist text pattern 
    fa_match = re.search(pattern=' \[ft\. .*\]', string=title)
    
    if fa_match:
        featured_arts = fa_match.group().lstrip(' [ft. ').rstrip(']')
        title = title.rstrip(fa_match.group())  #strip from title
    else:
        featured_arts = '-'
        
    if ', ' in featured_arts:
        print('multiple feature_arts???:\n' + featured_arts)
        
    # either way, once clear of featured's, strip the double quotes
    title = title.strip('“').strip('”').strip('"')
    
    return title, featured_arts



# works
def parse_body_rec_tag(bar):
    # parse recommendation tag for the title
    bnm = bar.findChild(attrs={'class': "bnm"}).contents[0]
    assert bnm, 'No bnm value for entry:\n'+str(bar)
    
    return bnm

# works
def parse_body_reviewer(bar):
    # parse reviewer name
    review_base = bar.findChild(attrs={'class': "linked display-name display-name--linked"})
    
    #if no reviewer
    if review_base:
        reviewer = review_base.getText().lstrip('by: ')
    else:
        reviewer='no-reviewer'
     
    return reviewer
        
#works
def parse_body_genre(bar):
    # genres can be multiple per entry
    genre_block = bar.findChildren(attrs={'class': 'genre-list__link'})
    genre_list = [genre.contents[0] for genre in genre_block]
    
    return genre_list

#works
def parse_body_pub_date(bar):
    """parse datetime from track-collection-item tag"""
    pub_dt = bar.findChild(attrs={'class': 'pub-date'}).attrs['datetime']
    
    return pub_dt
    
        
def parse_body_tag(tag):
   
    # parse artist name
    artist, other_artists = parse_body_artist(tag)
    
    # parse title, featured artists
    title, featured_arts = parse_body_title_fa(tag) 
        
    # parse recommendation tag for the track
    bnm = parse_body_rec_tag(tag)
    
    # parse reviewer name
    reviewer = parse_body_reviewer(tag)
    
    # parse genre list
    genre_list = parse_body_genre(tag)
    
    # get pub_date
    pub_dt = parse_body_pub_date(tag)
    
    tag_contents = [bnm, 
                    artist,
                    other_artists,
                    featured_arts,
                    title,
                    pub_dt,
                    reviewer, 
                    genre_list]
    
    return tag_contents


    
#%% main loop

def scrape_pitchfork(start=1, end=243, write_path=None):
    """main script to scrape pitchfork best tracks
    

    Parameters
    ----------
    start : int, optional
        Page to start scraping at. The default is 1.
    end : TYPE, optional
        page to stop scraping at. The default is 243, which was max as of 9/25/20.
    write_path : TYPE, optional
        if provided, location to write csv of output to. The default is None.

    Returns
    -------
    my_df : TYPE
        Pandas DataFrame of the scrape results.

    """
    t0=time.time()
    t2=time.time()
    
    results=[]
    # pages go to page 243 as of 9/25/20
    
    for c in range(243):    
        # off by 1 error
        i = c+1
        
        # get page
        page_soup = get_best_tracks_page(page_num=i)
        my_bod = get_page_track_results(page_soup)
        for tag in my_bod:
            results.append(parse_body_tag(tag))
        
        time.sleep(1)
    
        if not i%5:
            t1 = time.time()
            
            print('Completed page ' + str(i) + '.  lap: ' + str(t1-t2) + 's.  Total: ' + str(int((t1-t0)//60)) + 'm ' + str(int((t1-t0)%60))+'s')
            
            t2 = time.time()
                  
    my_df = pandas.DataFrame(results,
                             columns=['accolade',
                                      'artist',
                                      'other_artists',
                                      'featuring',
                                      'title',
                                      'pub_dt',
                                      'reviewer',
                                      'genre'])
    
    
    if write_path:
        my_df.to_csv(write_path)
    
    return my_df



# %%authorization variables

scope = 'user-top-read user-library-read playlist-read-private playlist-modify-private'

token = util.prompt_for_user_token('1254805075',
                                   scope=scope,
                                   client_id=spotify_client_id, # from config file
                                   client_secret=spotify_client_secret, # from config file
                                   redirect_uri='http://xkcd.com')


spot = spotipy.Spotify(auth=token)



#%%


search_art = 'Third Eye Blind'
search_track = 'Semi-Charmed Life'

query_raw = 'artist:' + search_art + ' name:' + search_track
query_clean = query_raw.replace(' ','+')




semilife = spot.search(q=query_raw, type='track')
    
# the href it's returning encodes colons as %3A, etc., which could be the source of the terrible search results.
# I should try rolling my own requester
print(semilife)

#teb_items = teb['artists']['items'][0]
#teb_id = teb['artists']['items'][0]['id']





#%% setting search queries for testing

# did f' all.  omitting field indicators seems more effective.
# 

search_type_options = ['artist', 'album', 'artist', 'playlist',
                       'track','show','episode']

search_type = 'track'  # 'artist', album , artist, playlist, track, show and episode. 
assert search_type in search_type_options, 'invalid type'


search_art = 'Big Thief'
search_track = 'Paul'
search_album = None
search_year = None

# assemble into query
search_dict = {'artist': search_art,
               'name': search_track,
               'album': search_album,
               'year': search_year}


#%% word bag search...


# construct query slug without filters
# query_stripped = ' '.join([val for val in search_dict.values() if val])

def query_simple_join(search_artist=None, search_track=None):
    """simple search 
    """
    # assemble into query
    search_dict = {'artist': search_artist,
                   'name': search_track}
    
    # join 
    simple_search = ' '.join([val for val in search_dict.values() if val])

    return simple_search



# search 
# query_term = spot.search(q=query_stripped, type='track')
# query_term['tracks']['items']
 
def clean_test_result(item):
    track_name = item['name']
    artist_list = [art['name'] for art in item['artists']]
    uri = item['uri']
    return [track_name, artist_list, uri]



def get_test_results(search_artist, search_track, query_plan, spot):
    """
    

    Parameters
    ----------
    search_artist : str
        artist name that we're searching for.
    search_track : str
        track title that we're searching for.
    query_plan : function
        function used to create the query.
    spot : TYPE
        spotify connection object.

    Returns
    -------
    test_results : list
        list of search results.

    """
        
    # apply query-writer to write query
    query_term = query_plan(search_artist=search_artist,
                            search_track=search_track)
    
    # search on api for the track
    test_search = spot.search(q=query_term, type='track')
    
    # extract results  to see if any match
    test_results = [clean_test_result(item) for item in test_search['tracks']['items']]
    
    return test_results
    


# testing on a track
get_test_results(search_artist='third eye blind', search_track='Jumper', query_plan=query_simple_join, spot=spot)


#%% trying to manually request


def aborted_manual_request_approach():
    """struggled to get the spotify search working well.  thought it might be
    an issue with spotipy encoding colons. tried to workaround by writing my
    own requester. Learned some stuff. Didn't solve the problem.
    """
    # did f' all.  omitting field indicators seems more effective.
    # 
    
    search_list = []
    
    for key, value in search_dict.items():
        if value:
            search_list.append(key + ':' + value)
        query_raw = '+'.join(search_list)
    
    
    
    # construct query slug
    query_raw = 'artist:' + search_art + ' name:' + search_track
    query_clean = query_raw.replace(' ','+')
    
    
    
    # base api search endpoint
    base_search_path = r'https://api.spotify.com/v1/search?q='
    
    
    search_url = base_search_path + query_clean + '&type=' + search_type
    
    spot._auth_headers() # gives me headers for manual request process

    foo = requests.get(search_url,
                       headers=spot._auth_headers())
    
    
    print(foo.json())


#%%


