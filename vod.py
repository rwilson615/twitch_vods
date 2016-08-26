import requests
import json
import argparse
import os

def getnauthTokens(id):
	pattern = 'https://api.twitch.tv/api/vods/{0}/access_token'
	url = pattern.format(id)

	r = requests.get(url)
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

	return r

def getLinkFromm3u(m3u):
	for line in m3u.iter_lines():
		if 'high' in line and not line.startswith('#'):
			return line
	raise Exception("No high quality link")
def truncLink(url):
	split = url.partition('high')
	return split[0] + split[1] + '/'

def getAlltsLinks(url):
	prefix = truncLink(url)
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

def downloadTS(id, links, path):
	count = 0
	listFile = open(path + '/list.m3u8', 'w')
	for link in links:
		r = requests.get(link)
		filename = path + '/' + id + '_' + str(count) + '.ts'
		with open(filename, 'wb') as output:
			print 'Writing' + str(count)
			output.write(r.content)
		count = count + 1
		lineToWrite = "file '" + filename + "'\n"
		listFile.write(lineToWrite)

def combine(path):
	print "Combining"
	os.system('ffmpeg -f concat -safe 0 -i ' + path + '/' + 'list.m3u8 -bsf:a aac_adtstoasc -c copy ' + path + '/' + 'output.mp4')

def downloadVod(args):
	m3u = getm3u(args.id)
	m3u8 = getLinkFromm3u(m3u)
	links = getAlltsLinks(m3u8)
	downloadTS(args.id, links, args.path)
	combine(args.path)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('id', help='The vod id to pull')
	parser.add_argument('path', help='The download Path')
	args = parser.parse_args()
	downloadVod(args)


if __name__ == "__main__":
	main()