from ASTNode import ASTNode


def gen_ast(tree, parent_node=None, initialize=True):
	if initialize:
		parent_node = ASTNode()
		parent_node.set_name("<root>")
	if tree:
		if type(tree) == str or type(tree) == bool:
			if parent_node.name == "qualifier":
				for factor in tree.split("."):
					current_node = ASTNode()
					current_node.set_name(factor)
					current_node.set_parent(parent_node)
					parent_node.append_child(current_node)
			else:
				current_node = ASTNode()
				current_node.set_name(tree)
				current_node.set_parent(parent_node)
				parent_node.append_child(current_node)
		elif type(tree) == set:
			for factor in tree:
				assert type(factor) == str
				current_node = ASTNode()
				current_node.set_name(factor)
				current_node.set_parent(parent_node)
				parent_node.append_child(current_node)
		elif type(tree) == list:
			for factor in tree:
				gen_ast(factor, parent_node, False)
		else:
			current_node = ASTNode()
			current_node.set_name(type(tree).__name__)
			current_node.set_parent(parent_node)
			parent_node.append_child(current_node)
			attrs = tree.attrs[:]
			children = tree.children[:]
			if current_node.name == "Cast":
				if hasattr(tree, "selectors"):
					attrs.append("selectors")
					children.append(tree.selectors)
			attrs, children = adjust_position(current_node, attrs, children)
			for i in range(len(attrs)):
				attr = attrs[i]
				child = children[i]
				if not child:
					continue
				attr_node = ASTNode()
				attr_node.set_name(attr)
				attr_node.set_parent(current_node)
				current_node.append_child(attr_node)
				gen_ast(child, attr_node, False)
	if initialize:
		return parent_node  # root node
	else:
		return None


def adjust_position(current_node, attrs, children):
	adjust_attrs = []
	adjust_children = []
	valid_attr_seq = []
	flag = False
	if current_node.name == "MethodInvocation":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "type_arguments", "member", "arguments", "selectors", "postfix_operators"]
	elif current_node.name == "MemberReference":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "member", "selectors", "postfix_operators"]
	elif current_node.name == "ReferenceType":
		flag = True
		valid_attr_seq = ["name", "arguments", "sub_type", "dimensions"]
	elif current_node.name == "This":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "selectors", "postfix_operators"]
	elif current_node.name == "ClassCreator":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "constructor_type_arguments", "type", "arguments", "body", "selectors", "postfix_operators"]
	elif current_node.name == "Literal":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "value", "selectors", "postfix_operators"]
	elif current_node.name == "ArrayCreator":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "type", "dimensions", "initializer", "selectors", "postfix_operators"]
	elif current_node.name == "BinaryOperation":
		flag = True
		valid_attr_seq = ["operandl", "operator", "operandr"]
	elif current_node.name == "":
		flag = True
		valid_attr_seq = ["expressionl", "type", "value"]
	elif current_node.name == "SuperMethodInvocation":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "type_arguments", "member", "arguments", "selectors", "postfix_operators"]
	elif current_node.name == "DoStatement":
		flag = True
		valid_attr_seq = ["label", "body", "condition"]
	elif current_node.name == "ClassReference":
		flag = True
		valid_attr_seq = ["prefix_operators", "qualifier", "type", "selectors", "postfix_operators"]
	elif current_node.name == "MethodReference":
		flag = True
		valid_attr_seq = ["expression", "type_arguments", "method"]
	elif current_node.name == "ClassDeclaration":
		flag = True
		valid_attr_seq = ["modifiers", "name", "type_parameters", "extends", "implements", "body"]
	elif current_node.name == "TypeArgument":
		flag = True
		valid_attr_seq = ["pattern_type", "type"]
	if flag:
		for factor in valid_attr_seq:
			if factor in attrs:
				adjust_attrs.append(factor)
				factor_index = attrs.index(factor)
				adjust_children.append(children[factor_index])
		return adjust_attrs, adjust_children
	else:
		return attrs, children

