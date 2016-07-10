#!/usr/bin/env python3

import sys, os, glob
import subprocess, re

import shadertool

section_pattern=re.compile('^\[(.*)\]')
def cleanup_dx9_ini(path, ini_prefix, removed_hashes):
	sections = set([ '[%s%s]' % (ini_prefix, os.path.splitext(x)[0]) for x in removed_hashes ])
	lines = open(path, newline='\n').readlines()

	current_section = None
	last_line = 0
	output = []
	section = []
	last_was_blank = False
	for line in lines:
		match = section_pattern.match(line)
		if match:
			last_was_blank = False
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
			if not last_was_blank and line.strip() == '' and last_line == len(section) - 1:
				# Allows stripping exactly 1 line of whitespace after the section
				last_line = len(section)
				last_was_blank = True
			else:
				last_was_blank = False

	if current_section not in sections:
		output.extend(section)
	else:
		output.extend(section[last_line:])

	open(path, 'w', newline='\n').write(''.join(output))

shaderoverride_pattern = re.compile('^\[ShaderOverride.*\]', re.IGNORECASE)
hash_pattern = re.compile(r'^\s*hash\s*=\s*([0-9a-f]+)\s*$', re.IGNORECASE)
def cleanup_dx11_ini(path, removed_hashes):
	hashes = set([ x.split('-', 1)[0] for x in removed_hashes ])
	lines = open(path, newline='\n').readlines()

	is_shaderoverride_section = False
	current_shaderoverride_hash = None
	last_line = 0
	output = []
	section = []
	last_was_blank = False
	for line in lines:
		if section_pattern.match(line):
			last_was_blank = False
			is_shaderoverride_section = not not shaderoverride_pattern.match(line)
			if current_shaderoverride_hash in hashes:
				output.extend(section[last_line:])
				current_shaderoverride_hash = None
				section = [line]
				last_line = 0
				continue
			output.extend(section)
			section = [line]
			current_shaderoverride_hash = None
			last_line = 0
		else:
			if is_shaderoverride_section:
				match = hash_pattern.match(line)
				if match:
					current_shaderoverride_hash = match.group(1)
			section.append(line)
			if line.strip() and line[0] != ';':
				last_line = len(section)
			if not last_was_blank and line.strip() == '' and last_line == len(section) - 1:
				# Allows stripping exactly 1 line of whitespace after the section
				last_line = len(section)
				last_was_blank = True
			else:
				last_was_blank = False

	if current_shaderoverride_hash not in hashes:
		output.extend(section)
	else:
		output.extend(section[last_line:])

	open(path, 'w', newline='\n').write(''.join(output))

def cleanup_common(game_dir, git_path, extracted_glob, shader_path, ini_filename, cleanup_ini):
	# TODO: Make case insensitive

	tmp = glob.glob(os.path.join(game_dir, extracted_glob))
	hashes = set([ os.path.basename(x) for x in tmp ])

	tmp = glob.glob(os.path.join(git_path, shader_path, '*.txt'))
	installed = set([ os.path.basename(x) for x in tmp ])

	removed_hashes = installed.difference(hashes)
	removed_files = [ os.path.join(shader_path, x) for x in removed_hashes ]

	if not removed_files:
		return

	command = ['git', '-C', git_path, 'rm'] + removed_files
	print("Running '%s'..." % ' '.join(command))
	subprocess.call(command)

	ini_path = os.path.join(git_path, ini_filename)
	cleanup_ini(ini_path, removed_hashes)

	command = ['git', '-C', git_path, 'add', ini_path]
	print("Running '%s'..." % ' '.join(command))
	subprocess.call(command)

	for file in removed_hashes:
		path = os.path.join(game_dir, shader_path, file)
		print("rm '%s'" % path)
		try:
			os.remove(path)
		except FileNotFoundError:
			pass

	cleanup_ini(os.path.join(game_dir, ini_filename), removed_hashes)

def cleanup_dx9(game_dir, git_path, unity_type, ini_prefix, helix_type):
	extracted_glob = 'extracted/ShaderCRCs/*/%s/*.txt' % unity_type
	shader_path = os.path.join('ShaderOverride', helix_type)
	ini_filename = 'DX9Settings.ini'
	cleanup_ini = lambda path, removed_hashes : cleanup_dx9_ini(path, ini_prefix, removed_hashes)
	return cleanup_common(game_dir, git_path, extracted_glob, shader_path, ini_filename, cleanup_ini)

def cleanup_dx11(game_dir, git_path):
	extracted_glob = 'extracted/ShaderFNVs/*/*.txt'
	shader_path = 'ShaderFixes'
	ini_filename = 'd3dx.ini'
	cleanup_ini = lambda path, removed_hashes : cleanup_dx11_ini(path, removed_hashes)
	return cleanup_common(game_dir, git_path, extracted_glob, shader_path, ini_filename, cleanup_ini)

def main():
	for game_dir in map(os.path.realpath, sys.argv[1:]):
		git_path = shadertool.game_git_dir(game_dir)
		found = False
		if os.path.exists(os.path.join(git_path, 'DX9Settings.ini')):
			cleanup_dx9(game_dir, git_path, 'vp', 'VS', 'VertexShaders')
			cleanup_dx9(game_dir, git_path, 'fp', 'PS', 'PixelShaders')
			found = True
		if os.path.exists(os.path.join(git_path, 'd3dx.ini')):
			cleanup_dx11(game_dir, git_path)
			found = True

		if found:
			command = [ 'git', '-C', git_path, 'commit', '-m', '%s: run cleanup_unity_shaders.py' % os.path.basename(git_path) ]
			print("Running '%s'..." % ' '.join(command))
			subprocess.call(command)
		else:
			print('cleanup_unity_shaders WARNING: Unable to determine modding tool for %s' % game_dir)

if __name__ == '__main__':
	main()
