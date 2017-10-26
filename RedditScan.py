#!/usr/bin/python

### a tool to curate a personal reading list of Reddit stories submitted by others
### to a private subreddit; acting like a news reader so that you don't miss 
### something interesting in the normal churn of Reddit. You could also use this
### to cross-post content to a public accessible subreddit, of course. 

### METHODOLOGY
### 1. Scan new submissions
### 2. Consider only URL submissions / no self-posts
### 3. Get enough key word hits on submission title, continue
### 4. Analyze the article submitted
### 5. Get enough key word hits (can be another value) on article body, continue
### 6. Post / X-post to target subreddit
### 7. I had this being ran by a cron and bash script just because; 
###	you can use any other alternative way to do this.
###
### Note: this relies upon the *user defined* titles on Reddit. This is
### sometimes a complete and total adventure, but I found it funny, so 
### I just went with it, despite Reddit titles being hyperbolic as hell.

### Ops:
### /root/reddit, use local praw.ini there / gets priority
### cron as follows: */5 * * * * cd /root/reddit&& /root/reddit/RedditScan.sh >/dev/null 2>&1
### that makes sure it's running, but only *one* instance is running
### everything else in the script is self-explanatory, follow notes
### This was something I did locally as I was experimenting with some logging, probably not
### needed for your purposes.

### to-do:
#
# track last 1000x titles to minimize dupes
# method to track last 1000x URLs to minimize dupes
# better logging
# method to further refine results 
# method to check cross posting of articles for title with highest upvotes to use submission.url of that
#
# Python style stuff; I'm a bash/sys admin/ops guy, so this probably looks ugly to real Python coders
# sorry!
#
###

# import
import praw
import pdb
import re
import os
import codecs
import random
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import urllib
import requests
import datetime

# Our oath
r = praw.Reddit('RedditScan')

## Settings
SUBREDDIT = 'all' # use /r/all to scan all of Reddit

### Lists to determine what to do
# These are the key words we're interested in. If title, URL, body match various instance gates
# e.g., two words in each of the title and URL, and then 8-10 instances in body

## NOTE: These are example triggers that I used for one particular reading list; anything else
## can be used and fine tuned and refined for whatever your interests are. 
## From my experimenting, the more things you add, the more refined your results
## will be over time versus a broader approach, but both can work according to your tastes.
## This can be done via regex, but at this time I found I was more satisfied consistently with
## incremental adjustments of these lists as presented. Your mileage may vary.

Topic_Triggers = [
'401k',
'bail out',
'big pharma',
'bitcoin',
'class war',
'concentration of wealth',
'competitiveness',
'congress',
'corporate concentration',
'corporate espionage',
'corporate executives',
'corporate tax rate',
'costs',
'currency manipulator',
'davos',
'debt crisis',
'debt repayment',
'default on loans',
'default on student loans',
'drug prices',
'economic competitiveness',
'economic inequality',
'economists agree',
'economy',
'employee',
'falling prices',
'fed audit',
'federal reserve',
'financial crisis',
'finances',
'foreign home buyers',
'freaknomics',
'government',
'government shutdown',
'government shuts down',
'great depression',
'great recession',
'guaranteed income',
'healthcare',
'health care',
'healh care costs',
'health-care costs',
'housing market',
'imf',
'income inequality',
'income share',
'inequality',
'insider trading',
'international trade',
'investing',
'investing in infrastructure',
'investment',
'investments',
'irs',
'loan subsidies',
'loan subsidy',
'low income',
'low-income',
'market',
'market cap',
'market value',
'minimum wage',
'monopoly',
'nafta trade deal',
'national debt',
'oil prices',
'opec',
'poverty rate',
'price hike',
'prices',
'raises interest rate',
'real estate bubble',
'richest families',
'savings accounts',
'shale',
'short-term profits',
'stadium subsidies',
'stock market',
'stock market crash',
'tax'
'top one percent',
'tourism',
'treasury',
'treasury department',
'tpp trade deal',
'united states',
'us economy',
'u.s. economy',
'u.s. healthcare',
'wage hikes',
'wealthiest 0.1%',
'wealthiest 1%',
'welfare dollars'
]

# skip any submissions by these people
# these are examples of user accounts who
# appear to be bots on Reddit doing similar things
# This helps to minimize duplication
# 
# Adjust per your tastes.
Author_blacklist = [
'-en-',
'autonewsadmin',
'autonewspaperadmin',
'mukhasim',
'thefeedbot',
'seculartalkbot'
]

# skip any submissions from these subreddits
# if you don't want to deal with noise from certain areas/subreddits
# 
# Adjust per your tastes.
Subreddit_blacklist = [
'autonewspaper',
'bitcoin',
'bitcoinall',
'economy',
'prepareforchange',
'pussypass',
'seculartalkvideos',
'the_donald',
'stockmarketnews'
]

# skip anything from these sites
# Your site/URL blacklist
# 
# Adjust per your tastes.
Site_blacklist = [
'.de/',
'blogspot.com',
'breitbart.com',
'circa.com',
'dailymail.co.uk',
'democratizeus.com',
'docs.google.com',
'en.europenews.dk',
'en.wikipedia.org',
'freebeacon.com',
'freerepublic.com',
'giphy.com',
'imgur.com',
'infowars.com',
'israelnationalnews.com',
'i.reddit.it',
'oann.com',
'prepareforchange.net',
'reddit.com',
'seekingalpha',
'stormfront.org',
'thenewamerican.com',
'twitter.com',
'washingtonexaminer.com',
'washingtontimes.com',
'wnd.com',
'wordpress.com',
'youtube.com',
'zerohedge.com',
'?feedType=RSS',
'thedavies.com',
'feedtype',
'messages.responder.co.il',
]


#### lets party
# scan submissions in stream
# run down a bunch of if/then gates
# post if we make it through the gauntlet
#
def SubmissionScan():
   for submission in r.subreddit('all').stream.submissions():
      # define per-submission variables
      titleWords = str(submission.title)
      urlWords = str(submission.url)
      authorWords = str(submission.author)
      subredditWords = str(submission.subreddit)
      # negative filters - self, site, author exclusions
      if not submission.is_self: # is not a self post on reddit
         if not any(ext in authorWords.lower() for ext in Author_blacklist): # author isn't on our author blacklist
            if not any(ext in urlWords.lower() for ext in Site_blacklist): # subreddit isn't on our site blacklist
               if not any(ext in subredditWords.lower() for ext in Subreddit_blacklist): # subreddit isn't on our subreddit blacklist
		  #
                  # positive triggers - do we meet thresholds in title, url, and body for inclusion?
                  # triggers - do they meet our topic word list?
		  # This is the "Title Gate", e.g. does the user submitted Reddit title
		  # have at least x number of instances from our Topic_Triggers list?
                  # For instance, if I used a value of "2", then we need two strings from
		  # that list to appear to pass this test. 
                  #
                  # recommendation: once your tests are satisfied with the title value,
                  # and a value of 2 to 3 seemed to work well for me, the next test for 
		  # reading the body worked best with about 3x this value.
		  #
                  if sum (word in str(titleWords).lower() for word in Topic_Triggers) >= 2:
                     print
                     print "###"
                     print datetime.datetime.now()
                     print "not self, not on site, author blacklist"
                     print "2+ hits in title from Triggers - examine the body for matches next"
                     print "Title: " + titleWords
                     print "URL: " + urlWords
                     print "Author: " + authorWords
                     print "Sub: " + subredditWords
                     # submission.hide() # hide the post so the bot can't see it again 
                     # submission.hide not needed here, perhaps, but may have value
                     # open web page
                     Title = submission.title
                     Link = submission.url
                     f = urllib.urlopen(Link)
                     Linkcontents = f.read()
		     #
		     # second positive trigger test - reading the contents of the article!
		     # as mentioned, it seemed to work well with 2-3 for title, and for this
		     # test I seemed to have the best results with a 3x value...
		     #
                     if sum (word in str(Linkcontents).lower() for word in Topic_Triggers) >= 7:
                        # write a log note that we submitted something
                        # stream will dump this to log if initiated off
                        # of the Badgov_initiate.sh monitor / restart  script
                        print "web content matches: post it!"
                        print datetime.datetime.now()
                        print "###"
                        print
                        # submit it
                        subreddit = r.subreddit('YourSubredditName') # THE SUBREDDIT WHERE YOU ARE POSTING
			#
			# NOTE: if you do this to someone else's subreddit, they almost certainly
		        # WILL NOT APPRECIATE IT, as it can be a flood of posts if you're not discrete
	                # in your filtering approach. Please test in a private subreddit!
			#
			# ask before unleashing this in someone else's subreddit.
			#
                        subreddit.submit(
                        title=Title,
                        url=Link,
                        resubmit=False, # todo: fix unhandled exceptions from this, eliminate need for supervisory script's aggressiveness
                        send_replies=False # no thanks
                        )

#### Engage

def runBot():
   SubmissionScan()
    
while True:
    runBot()
    
# end
