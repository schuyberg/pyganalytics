#!/usr/bin/python
# -*- coding: utf-8 -*-

import pprint
import sys
import codecs
import argparse
import yaml


# import the Auth Helper class
import auth

from apiclient.errors import HttpError
from oauth2client.client import AccessTokenRefreshError

from dateutil import rrule
from datetime import datetime, timedelta
import dateutil.parser

parser = argparse.ArgumentParser(description='Takes output file, config, secret')
parser.add_argument('-o','--output', help='Output file name',required=True)
parser.add_argument('-c', '--config', help='Configuration File Name', required=True)
parser.add_argument('-f', '--first', help='Harvest Start Date', required=True)
parser.add_argument('-l', '--last', help='Harvest End Date')
#parser.add_argument('-i', '--profile-id', help='Profile to Analyze (number', required=True)
#parser.add_argument('-p', '--property', help='Property to Analyze (number', required=True)

args = parser.parse_args()

#first = dateutil.parser.parse("2013-04-08")
first = dateutil.parser.parse(args.first)

if args.last: 
    last = dateutil.parser.parse(args.last)
else: 
    last = datetime.now()

#first = dateutil.parser.parse("2015-06-22")
#last = dateutil.parser.parse("2015-06-28")

#analyt = codecs.open('/media/Windows7_OS/dpla/new/dpla.analytics.weekly.csv', 'w', encoding='utf-8')
#logger = codecs.open('/media/Windows7_OS/dpla/new/analytics.log', 'a', encoding='utf-8')
#analyt.write("item|hits\n")
analyt = codecs.open(args.output, 'w', encoding='utf-8')
logger = codecs.open('analytics.log', 'a', encoding='utf-8')


with open(args.config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

header = ""
for dim in cfg['query']['dimensions'].split(","):
    header += dim + "|"
header += "count\n"
analyt.write(header)

logger.write("\n\n##########\n##### " + str(last) + "\n##########\n\n")

counts = {}

def main(argv):
  # Step 1. Get an analytics service object.
  service = auth.initialize_service()

  try:
    # Step 2. Get the user's first profile ID.
    #profile_id = get_first_profile_id(service)
    profile_id = str(cfg['profile'])
    print profile_id

    if profile_id:

        for sdate in rrule.rrule(rrule.WEEKLY, dtstart=first, until=last):
            edate = sdate + timedelta(days=6)
            print "Range is %s through %s" % (sdate.strftime("%Y-%m-%d"), edate.strftime("%Y-%m-%d"))
            logger.write("Range is %s through %s" % (sdate.strftime("%Y-%m-%d"), edate.strftime("%Y-%m-%d")))
            start = 1
            while start < 200000:
                print "Start = %s" % start
                data = get_data(service, profile_id, sdate.strftime("%Y-%m-%d"), edate.strftime("%Y-%m-%d"), start)
                store_data(data)
                print_pagination_info(data)
                print 'Next Link      = %s' % data.get('nextLink')
                logger.write("Hit Count = %s\n" % data.get('totalResults'))
                print 'Contains Sampled Data = %s' % data.get('containsSampledData')
                logger.write("Contains Sampled Data = %s\n\n" % data.get('containsSampledData'))

                if data.get('nextLink'): start += 10000
                else: start = 200000
    
        print_data(counts)

  except TypeError, error:
    # Handle errors in constructing a query.
    print ('There was an error in constructing your query : %s' % error)

  except HttpError, error:
    # Handle API errors.
    print ('Arg, there was an API error : %s : %s' %
           (error.resp.status, error._get_reason()))

  except AccessTokenRefreshError:
    # Handle Auth errors. 
    print ('The credentials have been revoked or expired, please re-run '
           'the application to re-authorize')

def get_results(service, profile_id):
  # Use the Analytics Service Object to query the Core Reporting API
  return service.data().ga().get(
      ids='ga:' + profile_id,
      start_date='2012-03-03',
      end_date='2012-03-03',
      metrics='ga:sessions').execute()

# Note from 20150405: Looks like the way to tweak this is going to be:
#metrics: ga:searcheUniques
#dimensions: ga:searchKeyword
#sort: -ga:searchUniques
#Curious if there's other interesting stuff to add here...

def get_data(service, profile_id, sdate, edate, start):
  # Use the Analytics Service Object to query the Core Reporting API
  return service.data().ga().get(
    ids='ga:' + profile_id,
    start_date=sdate,
    end_date=edate,
    #metrics='ga:hits',
    metrics=cfg['query']['metrics'],
    dimensions=cfg['query']['dimensions'],
    #sort='-ga:hits',
    sort=cfg['query']['sort'],    
    filters=cfg['query']['filters'],
    #filters='ga:pagepath=~^/item/c5cf1632a8a2c137c9b0e7b093024e0a',
    start_index=start,
    max_results='10000').execute()

# def get_data(service, profile_id, sdate, edate, start):
#   # Use the Analytics Service Object to query the Core Reporting API
#   return service.data().ga().get(
#     ids='ga:' + profile_id,
#     start_date=sdate,
#     end_date=edate,
#     metrics='ga:searcheUniques',
#     dimensions='ga:searchKeyword',
#     sort='-ga:searchUniques',
#     start_index=start,
#     max_results='10000').execute()

def print_results(results):
  # Print data nicely for the user.
  if results:
    print 'First View (Profile): %s' % results.get('profileInfo').get('profileName')
    print 'Total Sessions: %s' % results.get('rows')[0][0]

def store_data(data):
  # Print data nicely for the user.
  if data and type(data.get('rows')) == list:
    print 'Type: %s' % type(data)
    #pprint.pprint(data)
    print 'Data Length: %s' % len(data.get('rows'))
    print 'First Results: %s' % data.get('rows')[0]
    for row in data.get('rows'):
        dims = len(cfg['query']['dimensions'].split(","))
        key = ""
        for i in range(0,dims):
            key += row[i] + "|"
        key.rstrip("|")
        #print key.encode('utf-8')
        if key in counts: 
            counts[key] += int(row[dims])
        else:
            counts[key] = int(row[dims])
    #json +=  data.get('rows')

  else:
    print 'No results found'

def print_pagination_info(results):
  print 'Items per page = %s' % results.get('itemsPerPage')
  print 'Total Results  = %s' % results.get('totalResults')
  print 'Previous Link  = %s' % results.get('previousLink')
  print 'Next Link      = %s' % results.get('nextLink')

def print_data(counts):
    print 'Total Items = %s' % len(counts)
    for k, v in counts.iteritems():
        analyt.write(k + str(v) + "\n")

if __name__ == '__main__':
  main(sys.argv)