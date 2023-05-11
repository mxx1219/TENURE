import os
import pickle
import javalang
import sys


if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	
	parsed_data_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	out_package_dir = os.path.join(parsed_data_dir, "clazz_package_name.txt")
	buggy_file_path = os.path.join(parsed_data_dir, "completion_info/buggy_file.pkl")
	with open(buggy_file_path, "rb") as file:
		content = pickle.load(file)

	print(len(content))
	packages = []
	for factor in content:
		tokens = javalang.tokenizer.tokenize(factor)
		parser = javalang.parser.Parser(tokens)
		root = parser.parse()
		package_name = root.package
		print(package_name.name)
		packages.append(package_name.name)

	with open(out_package_dir, "w") as file:
		file.write("\n".join(packages))
