#!/usr/bin/env python3

import sys, os, glob
import subprocess, re

import shadertool

section_pattern=re.compile('^\[(.*)\]')
def cleanup_dx9_ini(path, sections):
	lines = open(path, newline='\n').readlines()

	current_section = None
	last_line = 0
	output = []
	section = []
	for line in lines:
		match = section_pattern.match(line)
		if section_pattern.match(line):
			if current_section in sections:
				output.extend(section[last_line:])
				current_section = match.group(0)
				section = [line]
				last_line = 0
				continue
			output.extend(section)
			section = [line]
			current_section = match.group(0)
			last_line = 0
		else:
			section.append(line)
			if line.strip() and line[0] != ';':
				last_line = len(section)

	if current_section not in sections:
		output.extend(section)
	else:
		output.extend(section[last_line:])

	open(path, 'w', newline='\n').write(''.join(output))


def cleanup_dx9(game_dir, git_path, unity_type, ini_prefix, helix_type):
	# TODO: Make case insensitive

	tmp = glob.glob(os.path.join(game_dir, 'extracted/ShaderCRCs/*/%s/*.txt' % unity_type))
	crcs = set([ os.path.basename(x) for x in tmp ])

	tmp = glob.glob(os.path.join(git_path, 'ShaderOverride/%s/*.txt' % helix_type))
	installed = set([ os.path.basename(x) for x in tmp ])

	removed_crcs = installed.difference(crcs)
	removed_files = [ 'ShaderOverride/%s/%s' % (helix_type, x) for x in removed_crcs ]

	if not removed_files:
		return

	command = ['git', '-C', git_path, 'rm'] + removed_files
	print("Running '%s'..." % ' '.join(command))
	subprocess.call(command)

	sections = set([ '[%s%s]' % (ini_prefix, os.path.splitext(x)[0]) for x in removed_crcs ])
	ini_path = os.path.join(git_path, 'DX9Settings.ini')
	cleanup_dx9_ini(ini_path, sections)

	command = ['git', '-C', git_path, 'add', ini_path]
	print("Running '%s'..." % ' '.join(command))
	subprocess.call(command)

	for file in removed_crcs:
		path = os.path.join(game_dir, 'ShaderOverride', helix_type, file)
		print("rm '%s'" % path)
		try:
			os.remove(path)
		except FileNotFoundError:
			pass

	cleanup_dx9_ini(os.path.join(game_dir, 'DX9Settings.ini'), sections)

def main():
	for game_dir in map(os.path.realpath, sys.argv[1:]):
		git_path = shadertool.game_git_dir(game_dir)
		cleanup_dx9(game_dir, git_path, 'vp', 'VS', 'VertexShaders')
		cleanup_dx9(game_dir, git_path, 'fp', 'PS', 'PixelShaders')

		command = [ 'git', '-C', git_path, 'commit', '-m', '%s: run cleanup_unity_shaders.py' % os.path.basename(git_path) ]
		print("Running '%s'..." % ' '.join(command))
		subprocess.call(command)

if __name__ == '__main__':
	main()
