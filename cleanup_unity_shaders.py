#!/usr/bin/env python3

import sys, os, glob
import subprocess, re, argparse

import shadertool

section_pattern=re.compile('^\[(.*)\]')
def cleanup_dx9_ini(path, ini_prefix, removed_basenames, preserve_basenames):
	if removed_basenames is not None:
		remove_sections = set([ '[%s%s]' % (ini_prefix, os.path.splitext(x)[0]) for x in removed_basenames ])
	if preserve_basenames is not None:
		preserve_sections = set([ '[%s%s]' % (ini_prefix, os.path.splitext(x)[0]) for x in preserve_basenames ])
	lines = open(path, newline='\n').readlines()

	def remove_section(section):
		if removed_basenames is not None:
			return section in remove_sections
		assert(preserve_basenames is not None)
		return section is not None and \
			section.startswith('[' + ini_prefix) and \
			section not in preserve_sections

	current_section = None
	last_line = 0
	output = []
	section = []
	last_was_blank = False
	for line in lines:
		match = section_pattern.match(line)
		if match:
			last_was_blank = False
			if remove_section(current_section):
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

	if remove_section(current_section):
		output.extend(section[last_line:])
	else:
		output.extend(section)

	open(path, 'w', newline='\n').write(''.join(output))

# TODO: Refactor with above function
shaderoverride_pattern = re.compile('^\[ShaderOverride.*\]', re.IGNORECASE)
hash_pattern = re.compile(r'^\s*hash\s*=\s*([0-9a-f]+)\s*$', re.IGNORECASE)
def cleanup_dx11_ini(path, removed_basenames, preserve_basenames):
	if removed_basenames is not None:
		remove_hashes = set([ x.split('-', 1)[0] for x in removed_basenames ])
	if preserve_basenames is not None:
		preserve_hashes = set([ x.split('-', 1)[0] for x in preserve_basenames ])
	lines = open(path, newline='\n').readlines()

	def remove_hash(hash):
		if removed_basenames is not None:
			return hash in remove_hashes
		assert(preserve_basenames is not None)
		return is_shaderoverride_section and hash not in preserve_hashes

	is_shaderoverride_section = False
	current_shaderoverride_hash = None
	last_line = 0
	output = []
	section = []
	last_was_blank = False
	for line in lines:
		if section_pattern.match(line):
			last_was_blank = False
			if remove_hash(current_shaderoverride_hash):
				output.extend(section[last_line:])
				is_shaderoverride_section = not not shaderoverride_pattern.match(line)
				current_shaderoverride_hash = None
				section = [line]
				last_line = 0
				continue
			output.extend(section)
			is_shaderoverride_section = not not shaderoverride_pattern.match(line)
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

	if remove_hash(current_shaderoverride_hash):
		output.extend(section[last_line:])
	else:
		output.extend(section)

	open(path, 'w', newline='\n').write(''.join(output))

def cleanup_ini_from_installed_only(game_dir, git_path, master_path, profile):
	tmp = glob.glob(os.path.join(master_path, profile.shader_path, '*.txt'))
	installed_basenames = set([ os.path.basename(x) for x in tmp ])

	if args.use_git:
		ini_path = os.path.join(git_path, profile.ini_filename)
		profile.cleanup_ini(ini_path, None, installed_basenames)

		command = ['git', '-C', git_path, 'add', profile.ini_filename]
		print("Running '%s'..." % ' '.join(command))
		subprocess.call(command)

	profile.cleanup_ini(os.path.join(game_dir, profile.ini_filename), None, installed_basenames)

def cleanup(game_dir, git_path, master_path, profile):
	if args.remove_ini_sections_for_uninstalled_shaders:
		return cleanup_ini_from_installed_only(game_dir, git_path, master_path, profile)

	# TODO: Make case insensitive
	tmp = glob.glob(os.path.join(game_dir, profile.extracted_glob))
	extracted_basenames = set([ os.path.basename(x) for x in tmp ])

	tmp = glob.glob(os.path.join(master_path, profile.shader_path, '*.txt'))
	installed_basenames = set([ os.path.basename(x) for x in tmp ])

	removed_basenames = installed_basenames.difference(extracted_basenames)
	removed_files = [ os.path.join(profile.shader_path, x) for x in removed_basenames ]

	if not removed_files:
		return

	if args.use_git:
		command = ['git', '-C', git_path, 'rm'] + removed_files
		print("Running '%s'..." % ' '.join(command))
		subprocess.call(command)

		ini_path = os.path.join(git_path, profile.ini_filename)
		profile.cleanup_ini(ini_path, removed_basenames, None)

		command = ['git', '-C', git_path, 'add', profile.ini_filename]
		print("Running '%s'..." % ' '.join(command))
		subprocess.call(command)

	for file in removed_basenames:
		path = os.path.join(game_dir, profile.shader_path, file)
		print("rm '%s'" % path)
		try:
			os.remove(path)
		except FileNotFoundError:
			pass

	profile.cleanup_ini(os.path.join(game_dir, profile.ini_filename), removed_basenames, None)

class CleanupDX9(object):
	def __init__(self, unity_type, ini_prefix, helix_type):
		self.extracted_glob = 'extracted/ShaderCRCs/*/%s/*.txt' % unity_type
		self.shader_path = os.path.join('ShaderOverride', helix_type)
		self.ini_filename = 'DX9Settings.ini'
		self.cleanup_ini = lambda path, removed_basenames, preserve_basenames : cleanup_dx9_ini(path, ini_prefix, removed_basenames, preserve_basenames)

class CleanupDX11(object):
	def __init__(self):
		self.extracted_glob = 'extracted/ShaderFNVs/*/*.txt'
		self.shader_path = 'ShaderFixes'
		self.ini_filename = 'd3dx.ini'
		self.cleanup_ini = lambda path, removed_basenames, preserve_basenames : cleanup_dx11_ini(path, removed_basenames, preserve_basenames)

def parse_args():
	global args
	parser = argparse.ArgumentParser(description = 'Stale Shader Removal Tool')
	parser.add_argument('games', nargs='+',
		help='List of game directories to process')
	parser.add_argument('--remove-ini-sections-for-uninstalled-shaders', action='store_true',
		help='Remove any ini sections for shaders not found in ShaderFixes/ShaderOverride. CAUTION: 3DMigoto does not require shaders to be installed to use with ini sections - this option will remove these!')
	parser.add_argument('--check-installed-from-game-dir', action='store_true',
		help='Use the game directory instead of the git directory to determine which shaders are installed')
	parser.add_argument('--no-git', dest='use_git', action='store_false',
		help="Do not update the copy of the fix tracked in git. CAUTION: If you aren't tracking the fix in git, make sure you have your own backup in case this script removes more than expected!")
	args = parser.parse_args()

def main():
	parse_args()
	for game_dir in map(os.path.realpath, args.games):
		if args.use_git:
			git_path = shadertool.game_git_dir(game_dir)
			if args.check_installed_from_game_dir:
				master_path = game_dir
			else:
				master_path = git_path
			if not os.path.exists(git_path):
				print('cleanup_unity_shaders: %s not tracked in git, skipping' % game_dir)
				continue
		else:
			git_path = None
			master_path = game_dir

		found = False
		if os.path.exists(os.path.join(master_path, 'DX9Settings.ini')):
			cleanup(game_dir, git_path, master_path, CleanupDX9('vp', 'VS', 'VertexShaders'))
			cleanup(game_dir, git_path, master_path, CleanupDX9('fp', 'PS', 'PixelShaders'))
			found = True
		if os.path.exists(os.path.join(master_path, 'd3dx.ini')):
			cleanup(game_dir, git_path, master_path, CleanupDX11())
			found = True

		if found:
			if args.use_git:
				command = [ 'git', '-C', git_path, 'commit', '-m', '%s: run %s' %
						(os.path.basename(git_path), ' '.join([os.path.basename(sys.argv[0])] + sys.argv[1:])) ]
				print("Running '%s'..." % ' '.join(command))
				subprocess.call(command)
		else:
			print('cleanup_unity_shaders WARNING: Unable to determine modding tool for %s' % game_dir)

if __name__ == '__main__':
	main()
