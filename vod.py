from __future__ import print_function
from simple_requests import Requests
import requests
import json
import argparse
import os
import shutil
import copy
import re

def getFileName(url):
	parts = url.split('/')
	return parts[len(parts) - 1]

def getnauthTokens(id):
	pattern = 'https://api.twitch.tv/api/vods/{0}/access_token'
	headers = {'Client-ID': 'k4liec7aunkujn6djfee2sb4ge56nj0'}
	url = pattern.format(id)

	r = requests.get(url, headers=headers)
	if r.status_code != 200:
		raise Exception("API returned {0}".format(r.status_code))

	j = r.json()
	return j

def getm3u(id):
	tokens = getnauthTokens(id)
	pattern = 'http://usher.twitch.tv/vod/{id_}?nauthsig={sig_}&nauth={token_}'
	url = pattern.format(id_=id, sig_=tokens['sig'], token_=tokens['token'])
	r = requests.get(url)
	if r.status_code != 200:
		raise Exception("API returned {0}".format(r.status_code))
	print(url)
	return r

def getLinkFromm3u(m3u):
	for line in m3u.iter_lines():
		if ('high' in line  or '1080p60' in line or '720p60' in line or '720p30' in line) and not line.startswith('#'):
			return line
	raise Exception("No high quality link")

def truncLink(url):
	if 'high' in url:
		split = url.partition('high')
	elif '1080p60' in url:
		split = url.partition('1080p60')
	elif '720p60' in url:
		split = url.partition('720p60')
	elif '720p30' in url:
		split = url.partition('720p30')
	return split[0] + split[1] + '/'

def getAlltsLinks(url):
	prefix = truncLink(url)
	print(prefix)
	r = requests.get(url)
	links = []
	if r.status_code != 200:
		raise Exception("API returned {0}".format(r.status_code))
	for line in r.iter_lines():
		if line == '':
			continue
		if line.startswith('#'):
			continue
		fullPath = prefix + line
		links.append(fullPath)
	return links

def getAllTS(id, links, path):
	requests = Requests(concurrent=10)
	for response in requests.swarm(links, maintainOrder=False):
			writeTS(path, response)

def writeTS(path, response):
	filename = path + getFileName(response.url)
	with open(filename, 'wb') as output:
		print('Writing ' + filename)
		output.write(response.content)

def createm3u8(path):
	files = []
	for file in sorted(os.listdir(path), key=lambda x: (int(re.sub('\D','',x)),x)):
		files.append("file '" + file + "'\n")
	with open(path + '/list.m3u8', 'w') as m3u8file:
		for line in files:
			m3u8file.write(line)

def combine(source, dest):
	print('Combining')
	os.system('ffmpeg -f concat -safe 0 -i ' + source + 'list.m3u8 -bsf:a aac_adtstoasc -c copy ' + dest + 'output.mp4')



def downloadVod(args):
	m3u = getm3u(args.id)
	print(m3u.text)
	m3u8 = getLinkFromm3u(m3u)
	links = getAlltsLinks(m3u8)
	if not os.path.exists(args.path + 'tmp'):
		os.mkdir(args.path + 'tmp')
	getAllTS(args.id, links, (args.path + 'tmp/'))
	createm3u8(args.path + 'tmp')
	combine((args.path + 'tmp/'), args.path)
	shutil.rmtree(args.path + 'tmp/')

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('id', help='The vod id to pull')
	parser.add_argument('path', help='The download Path')
	args = parser.parse_args()
	if not args.path.endswith('/'):
		args.path = args.path + '/'
	downloadVod(args)


if __name__ == "__main__":
	main()
