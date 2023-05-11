import os
import shutil
import sys
import time
import logging
import pickle
import re


def validate(version, version_still_trigger_tests, tests, cp_compile, cp_test, dir_build, buggy_file_path):
	parent_dir = "/".join(buggy_file_path.split("/")[:-1])
	file_name = buggy_file_path.split("/")[-1]
	compile_cmd = "cd {} && timeout 5s javac -cp {} -d {} {}".format(parent_dir, cp_compile, os.path.join(project_path, dir_build), file_name)
	#print(compile_cmd)
	status = os.system(compile_cmd)
	if status != 0:
		logging.info("False, False, False")
		return False, False
	fix_at_least_one = False
	current_fix_tests = []
	#print(tests)
	for test in tests:
		test_single_cmd = "timeout 5s java -Djava.awt.headless=true -cp {}:{}:{} SingleJUnitTestRunner {}".format(cp_test, junit_dir, single_test_runner_dir, test)
		#print(test_single_cmd)
		#exit(0)
		status = os.system(test_single_cmd)
		if status == 0:
			fix_at_least_one = True
			current_fix_tests.append(test)
	all_passed = False
	if fix_at_least_one:
		cmd = "cd {} && timeout 5m defects4j test".format(project_path)
		test_result = os.popen(cmd).readlines()
		for line in test_result:
			if line.strip().startswith("Failing tests:"):
				if int(line.replace("Failing tests: ", "").strip()) == 0:
					all_passed = True
				break
		if not all_passed:
			extra_failed = False
			for line in test_result:
				if line.strip().startswith("-"):
					current_failed = line.strip()[2:]
					if current_failed not in tests:
						extra_failed = True
						break
			fix_at_least_one = fix_at_least_one and not extra_failed
			if fix_at_least_one:
				for test in current_fix_tests:
					if test in version_still_trigger_tests[version]:
						version_still_trigger_tests[version].remove(test)
	logging.info("True, {}, {}".format(fix_at_least_one, all_passed))
	return fix_at_least_one, all_passed


if __name__ == "__main__":
	d4j_version = sys.argv[1]
	bug_version = sys.argv[2]
	fl_setting = sys.argv[3]
	BEAM = int(sys.argv[4])

	parsed_data_dir = "../parsed_data/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version)
	necessary_info_dir = "../necessary_info/d4j_{}".format(d4j_version)
	patch_dir = os.path.join(parsed_data_dir, "result/")
	patch_path = os.path.join(patch_dir, "patches_final.pkl")
	patch_ir_path = os.path.join(parsed_data_dir, "patch_irs.txt")
	project_path = os.path.abspath("../projects/d4j_{}/{}/".format(d4j_version, bug_version))
	position_path = os.path.join(parsed_data_dir, "method_position.txt")
	method_dir = os.path.join(parsed_data_dir, "data_no_empty_without_anno/")
	faulty_anno_path = os.path.join(parsed_data_dir, "fl_no_empty.txt")
	sample_info_path = os.path.join(parsed_data_dir, "completion_info/sample_info.txt")
	string_path = os.path.join(parsed_data_dir, "string_table.txt")
	trigger_info_path = os.path.join(necessary_info_dir, "trigger_tests.pkl")
	cp_compile_path = os.path.join(parsed_data_dir, "cp_compile.pkl")
	cp_test_path = os.path.join(parsed_data_dir, "cp_test.pkl")
	dir_build_path = os.path.join(necessary_info_dir, "dir_build.pkl")
	method_tmp_dir = "./file_storage/"
	patch_dir = "./patches/all/"
	partial_patch_dir = "./patches/partial/"
	single_test_runner_dir = "./junit_runner_{}/".format(d4j_version)
	junit_dir = "./junit-4.11.jar"
	log_dir = "./log/"
	HOURS = 5

	if not os.path.exists(method_tmp_dir):
		os.makedirs(method_tmp_dir)
	if not os.path.exists(patch_dir):
		os.makedirs(patch_dir)
		if not os.path.exists(os.path.join(patch_dir, "diff")):
			os.makedirs(os.path.join(patch_dir, "diff"))
		if not os.path.exists(os.path.join(patch_dir, "patch")):
			os.makedirs(os.path.join(patch_dir, "patch"))
	if not os.path.exists(partial_patch_dir):
		os.makedirs(partial_patch_dir)
		if not os.path.exists(os.path.join(partial_patch_dir, "diff")):
			os.makedirs(os.path.join(partial_patch_dir, "diff"))
		if not os.path.exists(os.path.join(partial_patch_dir, "patch")):
			os.makedirs(os.path.join(partial_patch_dir, "patch"))
	if not os.path.exists(log_dir):
		os.makedirs(log_dir)

	logging.basicConfig(filename=os.path.join(log_dir, "{}.log".format(bug_version)), level=logging.INFO)

	with open(sample_info_path, "r", encoding="utf-8") as file:
		content = file.readlines()
		version_info = []
		for line in content:
			line = line.strip()
			version = line.split(",")[0]
			buggy_file = line.split(",")[1]
			version_info.append((version, buggy_file))
	
	with open(faulty_anno_path, "r", encoding="utf-8") as file:
		content = file.readlines()
		faulty_annos = [factor.strip() for factor in content]
	curr_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
	logging.info("{} --> Current Version: {}".format(curr_time, bug_version))

	with open(string_path, "r", encoding="utf-8") as file:
		content = file.readlines()
		replace_strings = []
		for line in content:
			line = line.strip()
			if not line:
				replace_strings.append([])
			else:
				replace_strings.append(line.split(" <split> "))

	with open(position_path, "r", encoding="utf-8") as file:
		content = file.readlines()
		positions = []
		for line in content:
			line = line.strip()
			if not line:
				continue
			start_line = int(line.split(",")[0])
			end_line = int(line.split(",")[1])
			positions.append((start_line, end_line))

	with open(patch_ir_path, "r", encoding="utf-8") as file:
		nmt_results = file.readlines()
		nmt_results = [line.strip() for line in nmt_results]

	with open(patch_path, "rb") as file:
		results = pickle.load(file)
		final_results = []
		for i, cand_list in enumerate(results):
			if not cand_list:
				final_results.append([])
				continue
			final_cand_list = []
			for cand in cand_list:
				indices = [substr.start() for substr in re.finditer("\"STRING\"", cand)]
				if indices and len(indices) <= len(replace_strings[i//BEAM]):
					for j in range(len(indices)):
						start_index = cand.index("\"STRING\"")
						end_index = start_index + len("\"STRING\"")
						cand = cand[:start_index] + replace_strings[i//BEAM][j] + cand[end_index:]
					final_cand_list.append(cand)
				else:
					final_cand_list.append(cand)
			final_results.append(final_cand_list)
		results = final_results

	with open(trigger_info_path, "rb") as file:
		all_trigger_tests = pickle.load(file)

	with open(cp_compile_path, "rb") as file:
		cp_compile = pickle.load(file)

	with open(cp_test_path, "rb") as file:
		cp_test = pickle.load(file)

	with open(dir_build_path, "rb") as file:
		dir_build = pickle.load(file)

	last_buggy_file_path = "START_BUGGY_FILE"
	version_start_time = time.time()
	partial_patch_index = {}
	version_still_trigger_tests = {}
	already_fixed = False
	already_print = {}

	version_still_trigger_tests[bug_version] = all_trigger_tests[bug_version][:]
	already_print[bug_version] = False

	# Cannot normally compile and test
	should_speed = False
	for i in range(len(results)):
		# if find a patch can fix an unsolved failed test, then do not try the remaining candidates in the same beam result
		if should_speed:
			if i % BEAM != 0:
				continue
			else:
				should_speed = False
		if already_fixed:
			break
		cand_list = results[i]
		position = positions[i // BEAM]
		buggy_file_path = version_info[i // BEAM][1]
		faulty_anno = faulty_annos[i // BEAM]

		# time limit: 5 hours per version
		if time.time() - version_start_time > 3600 * HOURS:
			continue
		else:
			version_start_time = time.time()
			verison_changed = True
			logging.info("defects4j compile ...")
			cmd = "cd {} && timeout 2m defects4j compile".format(project_path)
			status = os.system(cmd)
			last_buggy_file_path = buggy_file_path
			
		if i % BEAM == 0:
			logging.info("========== {}".format(faulty_anno))
		# if the current focused file is changed, the origin version of last file needs to be compiled once by javac
		if not verison_changed and buggy_file_path != last_buggy_file_path:
			if last_buggy_file_path != "START_BUGGY_FILE":
				parent_dir = "/".join(last_buggy_file_path.split("/")[:-1])
				logging.info("javac compile ...")
				compile_cmd = "cd {} && timeout 5s javac -cp {} -d {} {}".format(parent_dir, cp_compile[bug_version], os.path.join(project_path, dir_build[bug_version]), last_buggy_file_path)
				status = os.system(compile_cmd)
			
			last_buggy_file_path = buggy_file_path
		correct_in_cand = False
		for result in cand_list:
			if correct_in_cand:
				break
			if already_fixed:
				break
			if " <unk> " in result or " <also_unk> " in result:
				continue
			if " \"STRING\" " in result:
				continue

			# backup and replace
			shutil.copy(buggy_file_path, os.path.join(method_tmp_dir, "{}.txt".format(bug_version)))
			try:
				with open(buggy_file_path, "r", encoding="utf-8") as file:
					lines = file.readlines()
			except:
				with open(buggy_file_path, "r", encoding="latin1") as file:
					lines = file.readlines()
			# delete the whole method
			if not result:
				annotation_start = position[0] - 2
				while annotation_start > 0:
					if lines[annotation_start].strip().startswith("@"):
						annotation_start -= 1
					else:
						break
				candidate = lines[:annotation_start + 1] + [result] + ["\n"] + lines[position[1]:]
			# normal situation
			else:
				candidate = lines[:position[0]-1] + [result] + ["\n"] + lines[position[1]:]
			
			with open(buggy_file_path, "w", encoding="utf-8") as file:
				file.write("".join(candidate))

			# validation
			pre_still_unfixed_count = len(version_still_trigger_tests[bug_version])
			fix_at_least_one, all_passed = validate(bug_version, version_still_trigger_tests, all_trigger_tests[bug_version], cp_compile[bug_version], cp_test[bug_version], dir_build[bug_version], buggy_file_path)
			curr_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
			logging.info("{} --> {}: ({}) {}".format(curr_time, bug_version, i % BEAM + 1, nmt_results[i]))

			if all_passed:
				logging.info("Successful")
				already_fixed = True
				with open(os.path.join(patch_dir, "patch", "{}.patch".format(bug_version)), "w", encoding="utf-8") as file:
					file.write(result)
				cmd = "diff {} {} > {}".format(os.path.join(method_dir, "{}.txt".format(i//BEAM + 1)),
											   os.path.join(patch_dir, "patch", "{}.patch".format(bug_version)),
											   os.path.join(patch_dir, "diff", "{}.diff".format(bug_version)))
				os.system(cmd)

			elif fix_at_least_one:
				correct_in_cand = True
				logging.info("Fix at least one test case.")
				if len(version_still_trigger_tests[bug_version]) < pre_still_unfixed_count:
					# if next version is the same, should speed up
					if i//BEAM+1 < len(version_info) and version_info[i//BEAM+1][0] == bug_version:
						should_speed = True
				if not already_print[bug_version] and len(version_still_trigger_tests[bug_version]) == 0:
					logging.info("Fix all triggered tests")
					already_print[bug_version] = True
				if bug_version not in partial_patch_index:
					partial_patch_index[bug_version] = 0
				partial_patch_index[bug_version] += 1
				with open(os.path.join(partial_patch_dir, "patch", "{}_{}.patch".format(bug_version, partial_patch_index[bug_version])), "w", encoding="utf-8") as file:
					file.write(result)
				cmd = "diff {} {} > {}".format(os.path.join(method_dir, "{}.txt".format(i // BEAM + 1)),
											   os.path.join(partial_patch_dir, "patch", "{}_{}.patch".format(bug_version, partial_patch_index[bug_version])),
											   os.path.join(partial_patch_dir, "diff", "{}_{}.diff".format(bug_version, partial_patch_index[bug_version])))
				os.system(cmd)

			else:
				logging.info("Failed")

			# restore
			shutil.copy(os.path.join(method_tmp_dir, "{}.txt".format(bug_version)), buggy_file_path)
