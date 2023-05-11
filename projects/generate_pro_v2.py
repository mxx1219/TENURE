import os

with open("v2.txt", "r") as file:
	content = file.readlines()
	content = [line.strip() for line in content]
if not os.path.exists("./d4j_v2/"):
	os.mkdir("./d4j_v2/")
for line in content:
	project = line.split("_")[0]
	version = line.split("_")[1]
	# should change jdk to 1.8 version (required by Defects4J-v2.0)
	cmd = "cd ./d4j_v2/ && defects4j checkout -p {} -v {} -w {}".format(project, version, line)
	os.system(cmd)
