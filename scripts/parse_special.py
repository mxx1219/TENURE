import os
import pickle
import sys

if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	if d4j_version != "v2":
		exit(0)
	cp_test_path = "../parsed_data/d4j_v2/{}/{}/cp_test.pkl".format(fl_setting, bug_version)
	with open(cp_test_path, "rb") as file:
		cp_test = pickle.load(file)
	cp_info = cp_test[bug_version]
	cp_info_list = cp_info.split(":")
	cp_info_list = [factor for factor in cp_info_list if "{" not in factor]
	cp_info = ":".join(cp_info_list)
	cp_test[bug_version] = cp_info
	with open(cp_test_path, "wb") as file:
		pickle.dump(cp_test, file)
	'''
	if "{" not in cp_info:
		exit(0)
	if bug_version == "Cli_27":
		cp_info = cp_info.replace("${test.classes.dir}", "target/test-classes")
		cp_info = cp_info.replace("${classes.dir}", "target/classes")
		cp_test[bug_version] = cp_info
	elif bug_version == "Cli_28":
		print(cp_info)		
	'''
