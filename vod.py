#!/usr/bin/env python
from __future__ import print_function
from simple_requests import Requests
from urlparse import urljoin
import requests
import json
import argparse
import os
import shutil
import copy
import re
import sys

def sorted_nicely( l ): 
	""" Sort the given iterable in the way that humans expect.""" 
	convert = lambda text: int(text) if text.isdigit() else text 
	alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
	return sorted(l, key = alphanum_key)

def getFileName(url):
	parts = url.split('/')
	return parts[len(parts) - 1]

def getnauthTokens(id, clientId):
	pattern = 'https://api.twitch.tv/api/vods/{0}/access_token'
	headers = {'Client-ID': clientId}
	url = pattern.format(id)

	r = requests.get(url, headers=headers)
	if r.status_code != 200:
		raise Exception("API returned {0}".format(r.status_code))

	j = r.json()
	return j

def getm3u(id, clientId):
	tokens = getnauthTokens(id, clientId)
	pattern = 'http://usher.twitch.tv/vod/{id_}?nauthsig={sig_}&nauth={token_}'
	url = pattern.format(id_=id, sig_=tokens['sig'], token_=tokens['token'])
	r = requests.get(url)
	if r.status_code != 200:
		raise Exception("API returned {0}".format(r.status_code))
	return r

def getLinkFromm3u(m3u):
	for line in m3u.iter_lines():
		if line.startswith('http'):
			print(line)
			return line

def getAlltsLinks(url):
	r = requests.get(url)
	links = []
	if r.status_code != 200:
		raise Exception("API returned {0}".format(r.status_code))
	for line in r.iter_lines():
		if line == '':
			continue
		if line.startswith('#'):
			continue
		fullPath = urljoin(url, line)
		links.append(fullPath)
	return links

def getAllTS(id, links, path, threads):
	requests = Requests(concurrent=threads)
	for response in requests.swarm(links, maintainOrder=False):
			writeTS(path, response)

def writeTS(path, response):
	filename = path + getFileName(response.url)
	with open(filename, 'wb') as output:
		print('Writing ' + filename)
		output.write(response.content)

def createm3u8(path):
	files = []
	listdir = os.listdir(path)
	if '.DS_Store' in listdir:
		listdir.remove('.DS_Store')
	for file in sorted_nicely(listdir):
		files.append("file '" + file + "'\n")
	with open(path + '/list.m3u8', 'w') as m3u8file:
		for line in files:
			m3u8file.write(line)

def combine(source, dest, filename):
	print('Combining')
	os.system('ffmpeg -f concat -safe 0 -i ' + source + 'list.m3u8 -bsf:a aac_adtstoasc -c copy ' + dest + filename)



def downloadVod(args, clientId):
	if clientId is not None and clientId != '':
		m3u = getm3u(args.vod_id, clientId)
	elif args.clientId is not None and clientId != '':
		m3u = getm3u(args.vod_id, args.clientId)
	else:
		sys.exit('ERROR: Need clientId specified in .twitchrc file or passed in as argument')
	m3u8 = getLinkFromm3u(m3u)
	links = getAlltsLinks(m3u8)
	if os.path.exists(args.path + 'tmp'):
		shutil.rmtree(args.path + 'tmp')
	os.mkdir(args.path + 'tmp')
	getAllTS(args.vod_id, links, (args.path + 'tmp/'), args.threads)
	createm3u8(args.path + 'tmp')
	combine((args.path + 'tmp/'), args.path, args.output)
	shutil.rmtree(args.path + 'tmp/')

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('vod_id', help='The ID of the Twitch VOD to download')
	parser.add_argument('path', help='The path to save the download')
	parser.add_argument('-c', '--clientId', help='The client id for the twitch client')
	parser.add_argument('-o', '--output', help='The filename for the downloaded VOD', default='output.mp4')
	parser.add_argument('-t', '--threads', help='The number of concurrent requests allowed', type=int, default='10')
	args = parser.parse_args()
	if not args.path.endswith('/'):
		args.path = args.path + '/'
	clientId = None
	if os.path.isfile(os.path.expanduser('~') + '/.twitchrc'):
		print ('Twitch path exists')
		clientFile = open(os.path.expanduser('~')+'/.twitchrc', 'r')
		clientId = clientFile.readline()
		clientFile.close()	
	downloadVod(args, clientId)


if __name__ == "__main__":
	main()
