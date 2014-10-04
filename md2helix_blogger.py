#!/usr/bin/env python

'''
Format markdown into HTML to be a bit more consistent with the formatting on
the Helix blog:
- Strip <h1>, since that will be on the page title
- Replace <h2> with <p><u>
'''

import markdown
from markdown.util import etree

class md2helixExtension(markdown.extensions.Extension):
	def extendMarkdown(self, md, md_globals):
		md.treeprocessors.add('md2helix_blogger', md2helixProcessor(), '_end')

class md2helixProcessor(markdown.treeprocessors.Treeprocessor):
	def run(self, root):
		for node in root:
			# Only remove top-level h1 tags since getiterator won't
			# track parents, and I don't care about sub-levels.
			if node.tag == 'h1':
				print '___REMOVING HEADER: "%s"___' % node.text
				root.remove(node)
		for node in root.getiterator():
			if node.tag == 'h2':
				print 'Downgrading header: "%s"' % node.text
				node.tag = 'p'
				child = etree.SubElement(node, 'u')
				child.text = node.text
				node.text = ""
		return root

if __name__ == '__main__':
	import sys
	if len(sys.argv) != 3:
		print 'Usage: %s in.md out.html'
		sys.exit(1)
	f_in = open(sys.argv[1], 'r')
	f_out = open(sys.argv[2], 'w')

	ext = md2helixExtension()

	html = markdown.markdown(f_in.read(), extensions=[ext])
	f_out.write(html)
