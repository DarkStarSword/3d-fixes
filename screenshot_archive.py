#!/usr/bin/env python3

import os, re, time

pattern = re.compile(r'(?P<game>.*)\d\d(?:_\d)?\d.(?P<extension>jps|pns)', re.IGNORECASE)

def archive():
	for filename in os.listdir(os.curdir):
		if not os.path.isfile(filename):
			continue
		match = pattern.match(filename)
		if match is None:
			continue

		cur_time = time.mktime(time.localtime())
		timestamp = time.localtime(os.stat(filename).st_mtime)
		timestamp_str = time.strftime('%Y-%m-%d - %H%M%S', timestamp)

		if cur_time - time.mktime(timestamp) < 10:
			print('Skipping %s for now - young file' % filename)
			continue

		game = match.group('game')
		if not os.path.exists(game):
			os.mkdir(game, 0o0700)
		elif not os.path.isdir(game):
			raise TypeError("%s is not a directory" % game)

		i = 0
		while True:
			new_filename = os.path.join(game, '%s - %s.%i.%s' % (game, timestamp_str, i, match.group('extension')))
			if not os.path.exists(new_filename):
				break
			i += 1

		print('%s -> %s' % (filename, new_filename))
		os.rename(filename, new_filename)
		os.chmod(new_filename, 0o0600)

def main():
	while True:
		archive()
		print('.')
		time.sleep(20)

if __name__ == '__main__':
	main()
