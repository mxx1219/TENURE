import os
import javalang


class ASTNode():
	def __init__(self):
		self.node_type = ""
		self.parent = None
		self.children = []
		self.start = -1
		self.end = -1
		self.deepest_child = None
		self.is_stmt = False
		self.origin_node = None
							
	def append_child(self, child):
		self.children.append(child)
	
	def set_parent(self, parent):
		self.parent = parent

	def set_type(self, node_type):
		self.node_type = node_type

	def set_start(self, start):
		self.start = start
	
	def set_end(self, end):
		self.end = end
	
	def set_ifstmt(self, is_stmt):
		self.is_stmt = is_stmt

	def set_deepest_child(self, deepest_child):
		self.deepest_child = deepest_child

	def set_origin_node(self, origin_node):
		self.origin_node = origin_node


def parse_children(node, parent, node_list):
	if node:
		if type(node) == list:
			for child in node:
				parse_children(child, parent, node_list)
		elif isinstance(node, javalang.tree.Node):
			ast_node = ASTNode()
			if node.position:
				ast_node.set_start(node.position[0])
			ast_node.set_type(type(node).__name__)
			parent.append_child(ast_node)
			ast_node.set_parent(parent)
			ast_node.set_origin_node(node)
			node_list.append(ast_node)
			if isinstance(node, javalang.tree.Statement) or type(node).__name__ == "LocalVariableDeclaration":
				ast_node.is_stmt = True
			for child in node.children:
				parse_children(child, ast_node, node_list)


def get_endline(astnode, ancestor):
	for child in astnode.children:
		if child.start > ancestor.end:
			ancestor.deepest_child = child
			ancestor.end = child.start
		get_endline(child, ancestor)


def solve_blocks(node, child):
	if child == node:
		return
	if child.node_type == "BlockStatement":
		node.end += 1
	parent = child.parent
	solve_blocks(node, parent)


def parse_stmt(method):
	lines = method.split("\n")
	anno_line = -1
	for i, line in enumerate(lines):
		if line.strip().startswith("rank2fixstart"):
			anno_line = i + 2
	assert anno_line != -1
	
	clazz = "public class Tmp { \n" + method + "\n}"
	clazz = clazz.replace("rank2fixstart", "").replace("rank2fixend", "")

	tokens = javalang.tokenizer.tokenize(clazz)
	parser = javalang.parser.Parser(tokens)
	root = parser.parse()

	root_node = ASTNode()
	node_list = []
	for node in root.children:
		parse_children(node, root_node, node_list)
	
	stmt_list = []
	anno_stmt = None
	for node in node_list:
		if node.is_stmt:
			if node.node_type != "BlockStatement":
				get_endline(node, node)
				if node.deepest_child:
					solve_blocks(node, node.deepest_child)
				if node.end == -1:
					node.end = node.start
				stmt_list.append(node)
	for stmt in stmt_list:
		stmt.set_start(stmt.start - 1)
		stmt.set_end(stmt.end - 1)
		if stmt.start == anno_line - 1:
			anno_stmt = stmt
	return stmt_list, anno_stmt
