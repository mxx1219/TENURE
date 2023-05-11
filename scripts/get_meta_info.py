import os
import pickle
import sys

if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]

	project_dir = "../projects/d4j_{}/{}/".format(d4j_version, bug_version)
	parsed_data_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	cp_compile_path = os.path.join(parsed_data_dir, "cp_compile.pkl")
	cp_test_path = os.path.join(parsed_data_dir, "cp_test.pkl")

	cp_compile = {}
	cp_test = {}

	cmd = "cd {} && defects4j export -p cp.compile".format(project_dir)
	try:
		cp = os.popen(cmd).readlines()[0].strip()
	except:
		cp = ""
	cp_compile[bug_version] = cp

	cmd = "cd {} && defects4j export -p cp.test".format(project_dir)
	try:
		cp = os.popen(cmd).readlines()[0].strip()
	except:
		cp = ""
	cp_test[bug_version] = cp

	with open(cp_compile_path, "wb") as file:
		pickle.dump(cp_compile, file)
	
	with open(cp_test_path, "wb") as file:
		pickle.dump(cp_test, file)
