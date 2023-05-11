import os

d4j_version = ["v1", "v2"]
for part in d4j_version:
	for file_name in os.listdir("../projects/d4j_{}/".format(part)):
		if os.path.exists(os.path.join("../projects/d4j_{}/".format(part), file_name, ".git/index.lock")):
			print("exists")
		cmd = "cd {} && git checkout -- .".format(os.path.join("../projects/d4j_{}/".format(part), file_name))
		print(cmd)
		status = os.system(cmd)
		if status != 0:
			print("Error!")
			exit(-1)
		cmd = "cd {} && git clean -fd".format(os.path.join("../projects/d4j_{}".format(part), file_name))
		print(cmd)
		status = os.system(cmd)
		if status != 0:
			print("Error!")
			exit(-1)
