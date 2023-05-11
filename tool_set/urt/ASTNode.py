class ASTNode():
	def __init__(self):
		self.children = []
		self.parent = None
		self.name = None

	def set_parent(self, parent):
		self.parent = parent

	def append_child(self, child):
		self.children.append(child)

	def set_name(self, name):
		self.name = name
