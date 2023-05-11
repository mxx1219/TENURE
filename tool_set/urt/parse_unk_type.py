def parse_unk_type(node):
	if node.parent.parent.name == "MethodInvocation":
		if node.parent.name == "member":
			if node.parent.parent.parent and node.parent.parent.parent.name == "selectors" \
				and node.parent.parent.parent.parent and node.parent.parent.parent.parent.name == "This":
				return "this_method_member"
			else:
				return "method_member"
		elif node.parent.name == "qualifier":
			return "method_qualifier"
	elif node.parent.parent.name == "MemberReference":
		if node.parent.name == "member":
			if node.parent.parent.parent and node.parent.parent.parent.name == "selectors" \
				and node.parent.parent.parent.parent and node.parent.parent.parent.parent.name == "This":
				return "this_variable_member"
			else:
				return "variable_member"
		elif node.parent.name == "qualifier":
			return "variable_qualifier"
	elif node.parent.parent.name == "SuperMemberReference":
		if node.parent.name == "member":
			return "super_variable_member"
	elif node.parent.parent.name == "SuperMethodInvocation":
		if node.parent.name == "member":
			return "super_method_member"
	elif node.parent.parent.name == "ReferenceType":
		if node.parent.name == "name":
			if node.parent.parent.parent and node.parent.parent.parent.name == "return_type":
				return "return_type"
			else:
				return "type_name"
	elif node.parent.parent.name == "VariableDeclarator":
		if node.parent.name == "name":
			return "variable_dec_name"
	elif node.parent.parent.name == "MethodDeclaration":
		if node.parent.name == "name":
			return "method_dec_name"
		elif node.parent.name == "throws":
			return "method_dec_throws"
	elif node.parent.parent.name == "ConstructorDeclaration":
		if node.parent.name == "name":
			return "constructor_dec_name"
	elif node.parent.parent.name == "FormalParameter":
		if node.parent.name == "name":
			return "parameter_name"
	elif node.parent.parent.name == "This":
		if node.parent.name == "qualifier":
			return "outer_class_qualifier"
	elif node.parent.parent.name == "SuperMethodInvocation":
		if node.parent.name == "member":
			return "super_method_member"
	elif node.parent.parent.name == "CatchClauseParameter":
		if node.parent.name == "types":
			return "catch_type"
	elif node.parent.parent.name == "ClassReference":  # i.g. "java.lang" is the qualifier and "Runtime" is the type in "java.lang.Runtime.class"
		if node.parent.name == "qualifier":
			return "class_reference"
	elif node.parent.parent.name == "TryResource":
		if node.parent.name == "name":
			return "try_resource_name"
	return None
