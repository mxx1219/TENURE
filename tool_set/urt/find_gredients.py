def find_method_decl_name(node):
	if node.parent and node.parent.name == "name":
		if node.parent.parent and node.parent.parent.name == "MethodDeclaration":
			return node.name
	for child in node.children:
		result = find_method_decl_name(child)
		if result:
			return result
	return None


def find_constructor_decl_name(node):
	if node.parent and node.parent.name == "name":
		if node.parent.parent and node.parent.parent.name == "ConstructorDeclaration":
			return node.name
	for child in node.children:
		result = find_constructor_decl_name(child)
		if result:
			return result
	return None


def find_return_type(node):
	if node.parent and node.parent.name == "name":
		if node.parent.parent and node.parent.parent.name == "ReferenceType":
			if node.parent.parent.parent and node.parent.parent.parent.name == "return_type":
				return node.name
	for child in node.children:
		result = find_return_type(child)
		if result:
			return result
	return None


def find_parameter_names(node, candidate_list):
	if node.parent and node.parent.name == "name":
		if node.parent.parent and node.parent.parent.name == "FormalParameter":
			candidate_list.append(node.name)
	for child in node.children:
		find_parameter_names(child, candidate_list)


def find_variable_decl_names(node, candidate_list):
	if node.parent and node.parent.name == "name":
		if node.parent.parent and node.parent.parent.name == "VariableDeclarator":
			candidate_list.append(node.name)
	for child in node.children:
		find_variable_decl_names(child, candidate_list)


def find_type_names(node, candidate_list):
	if node.parent and node.parent.name == "name":
		if node.parent.parent and node.parent.parent.name == "ReferenceType":
			candidate_list.append(node.name)
	for child in node.children:
		find_type_names(child, candidate_list)


def find_method_members(node, candidate_list):
	if node.parent and node.parent.name == "member":
		if node.parent.parent and node.parent.parent.name == "MethodInvocation":
			candidate_list.append(node.name)
	for child in node.children:
		find_method_members(child, candidate_list)


def find_method_qualifiers(node, candidate_list):
	if node.parent and node.parent.name == "qualifier":
		if node.parent.parent and node.parent.parent.name == "MethodInvocation":
			candidate_list.append(node.name)
	for child in node.children:
		find_method_qualifiers(child, candidate_list)


def find_variable_members(node, candidate_list):
	if node.parent and node.parent.name == "member":
		if node.parent.parent and node.parent.parent.name == "MemberReference":
			candidate_list.append(node.name)
	for child in node.children:
		find_variable_members(child, candidate_list)


def find_variable_qualifiers(node, candidate_list):
	if node.parent and node.parent.name == "qualifier":
		if node.parent.parent and node.parent.parent.name == "MemberReference":
			candidate_list.append(node.name)
	for child in node.children:
		find_variable_qualifiers(child, candidate_list)


def find_this_method_members(node, candidate_list):
	if node.parent and node.parent.name == "member":
		if node.parent.parent and node.parent.parent.name == "MethodInvocation":
			if node.parent.parent.parent and node.parent.parent.parent.name == "selectors":
				if node.parent.parent.parent.parent and node.parent.parent.parent.parent.name == "This":
					candidate_list.append(node.name)
	for child in node.children:
		find_this_method_members(child, candidate_list)


def find_this_variable_members(node, candidate_list):
	if node.parent and node.parent.name == "member":
		if node.parent.parent and node.parent.parent.name == "MemberReference":
			if node.parent.parent.parent and node.parent.parent.parent.name == "selectors":
				if node.parent.parent.parent.parent and node.parent.parent.parent.parent.name == "This":
					candidate_list.append(node.name)
	for child in node.children:
		find_this_variable_members(child, candidate_list)
