def find_unk_nodes(node, unk_list):
	if node.name == "rank2fixunk":
		unk_list.append(node)
	for child in node.children:
		find_unk_nodes(child, unk_list)


def judge_class_relationship(current_class, compared_class, class_info):
	if current_class in class_info:
		if current_class == compared_class:
			return "same_class"
		elif class_info[current_class]["package"] == class_info[compared_class]["package"]:
			return "same_package"
		else:
			return "not_same_package"
	else:
		return "not_same_package"


def parse_argument_type(arguments, var_type, current_class, class_info):  # need to extend
	arg_types = []
	try:
		for arg in arguments:
			if arg.name == "MemberReference":
				var_name = ""
				qualifier_name = ""
				for child in arg.children:
					if child.name == "member":
						var_name = child.children[0].name
					elif child.name == "qualifier":
						qualifier_name = child.children[0].name
				if not qualifier_name:
					if var_name in var_type:
						arg_types.append(var_type[var_name])
					elif current_class in class_info:
						fields = class_info[current_class]["fields"]
						flag = False
						for field in fields:
							if field["name"] == var_name:
								arg_types.append(field["type"])
								flag = True
								break
						if not flag:
							arg_types.append("<unknown_type>")
					else:
						arg_types.append("<unknown_type>")
				else:
					class_type = None
					if qualifier_name in var_type:
						class_type = var_type[qualifier_name]
					if not class_type:
						if current_class in class_info:
							fields = class_info[current_class]["fields"]
							for field in fields:
								if field["name"] == qualifier_name:
									class_type = field["type"]
					if not class_type:
						if qualifier_name in class_info:  # for static field
							class_type = qualifier_name
					if class_type and class_type in class_info:
						flag = False
						for field in class_info[class_type]["fields"]:
							if field["name"] == var_name:
								arg_types.append(field["type"])
								flag = True
								break
						if not flag:
							arg_types.append("<unknown_type>")
					else:
						arg_types.append("<unknown_type>")
			elif arg.name == "MethodInvocation":
				method_name = ""
				qualifier_name = ""
				for child in arg.children:
					if child.name == "member":
						method_name = child.children[0].name
					elif child.name == "qualifier":
						qualifier_name = child.children[0].name
				if not qualifier_name:
					if current_class in class_info:
						methods = class_info[current_class]["methods"]
						flag = False
						for method in methods:
							if method["name"] == method_name:
								arg_types.append(method["type"])
								flag = True
								break
						if not flag:
							arg_types.append("<unknown_type>")
					else:
						arg_types.append("<unknown_type>")
				else:
					class_type = None
					if qualifier_name in var_type:
						class_type = var_type[qualifier_name]
					if not class_type:
						if current_class in class_info:
							fields = class_info[current_class]["fields"]
							for field in fields:
								if field["name"] == qualifier_name:
									class_type = field["type"]
					if not class_type:
						if qualifier_name in class_info:  # for static method
							class_type = qualifier_name
					if class_type and class_type in class_info:
						flag = False
						for method in class_info[class_type]["methods"]:
							if method["name"] == method_name:
								arg_types.append(method["type"])
								flag = True
								break
						if not flag:
							arg_types.append("<unknown_type>")
					else:
						arg_types.append("<unknown_type>")

			else:
				arg_types.append("<unknown_type>")
	except:
		print("Parsing argument error!")
	return arg_types


def get_all_multi_child_rule(node, rule_list):
	if len(node.children) > 1 and node.name != "body" and node.name != "block" and node.name != "statements":
		child_names = []
		for child in node.children:
			child_names.append(child.name)
		rule_list.append("{} -> {}".format(node.name, ",".join(child_names)))
	for child in node.children:
		get_all_multi_child_rule(child, rule_list)


def find_field_in_super_clazz(class_info, current_clazz, field_name, parse_current=False):
	if current_clazz not in class_info:
		return None
	else:
		if parse_current:
			fields = class_info[current_clazz]["fields"]
			for field in fields:
				if field["name"] == field_name:
					return field["type"]
		if not class_info[current_clazz]["super_class"]:
			return None
		else:
			field_type = None
			for super_clazz in class_info[current_clazz]["super_class"]:
				field_type = find_field_in_super_clazz(class_info, super_clazz, field_name, True)
				if field_type:
					break
			return field_type


def parse_super_class(current_class, class_info, ancestor_list):
	if current_class in class_info:
		super_clazz_list = class_info[current_class]["super_class"]
		for super_clazz in super_clazz_list:
			ancestor_list.append(super_clazz)
			parse_super_class(super_clazz, class_info, ancestor_list)



